use std::io::{Read, Write};
use std::net::TcpStream;
use std::sync::{Arc, Barrier};
use std::thread;
use std::time::Instant;

const REQUEST: &[u8] =
    b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: keep-alive\r\n\r\n";

fn content_length(head: &[u8]) -> usize {
    let needle = b"content-length:";
    let lower = head.to_ascii_lowercase();
    if let Some(pos) = lower.windows(needle.len()).position(|w| w == needle) {
        let mut i = pos + needle.len();
        while i < lower.len() && (lower[i] == b' ' || lower[i] == b'\t') {
            i += 1;
        }
        let mut n = 0usize;
        while i < lower.len() && lower[i].is_ascii_digit() {
            n = n * 10 + (lower[i] - b'0') as usize;
            i += 1;
        }
        return n;
    }
    0
}

fn read_response(stream: &mut TcpStream, buf: &mut [u8], len: &mut usize) -> bool {
    loop {
        if let Some(h) = buf[..*len].windows(4).position(|w| w == b"\r\n\r\n") {
            let body = h + 4;
            let cl = content_length(&buf[..body]);
            if *len >= body + cl {
                let consumed = body + cl;
                buf.copy_within(consumed..*len, 0);
                *len -= consumed;
                return true;
            }
        }
        match stream.read(&mut buf[*len..]) {
            Ok(0) => return false,
            Ok(n) => *len += n,
            Err(_) => return false,
        }
        if *len == buf.len() {
            return false;
        }
    }
}

fn pct(sorted: &[u64], p: f64) -> u64 {
    if sorted.is_empty() {
        return 0;
    }
    let idx = ((sorted.len() as f64 - 1.0) * p).round() as usize;
    sorted[idx]
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let addrs: Vec<String> = args
        .get(1)
        .cloned()
        .unwrap_or_else(|| "127.0.0.1:18092".into())
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();
    let concurrency: usize = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(16);
    let total: usize = args.get(3).and_then(|s| s.parse().ok()).unwrap_or(20000);
    let warmup: usize = args.get(4).and_then(|s| s.parse().ok()).unwrap_or(200);

    let base = total / concurrency;
    let rem = total % concurrency;
    let barrier = Arc::new(Barrier::new(concurrency + 1));
    let mut joins = Vec::new();
    for t in 0..concurrency {
        let addr = addrs[t % addrs.len()].clone();
        let barrier = barrier.clone();
        let n = base + if t < rem { 1 } else { 0 };
        joins.push(thread::spawn(move || -> Result<Vec<u64>, String> {
            let mut stream = TcpStream::connect(&addr).map_err(|e| e.to_string())?;
            let _ = stream.set_nodelay(true);
            let mut buf = [0u8; 65536];
            let mut len = 0usize;
            for _ in 0..warmup {
                if stream.write_all(REQUEST).is_err() || !read_response(&mut stream, &mut buf, &mut len) {
                    return Err("warmup io".into());
                }
            }
            barrier.wait();
            let mut lat = Vec::with_capacity(n);
            for _ in 0..n {
                let start = Instant::now();
                if stream.write_all(REQUEST).is_err() || !read_response(&mut stream, &mut buf, &mut len) {
                    return Err("io".into());
                }
                lat.push(start.elapsed().as_nanos() as u64);
            }
            Ok(lat)
        }));
    }
    barrier.wait();
    let start = Instant::now();
    let mut all = Vec::with_capacity(total);
    let mut errors = 0usize;
    for j in joins {
        match j.join() {
            Ok(Ok(mut v)) => all.append(&mut v),
            _ => errors += 1,
        }
    }
    let elapsed = start.elapsed().as_secs_f64();
    all.sort_unstable();
    let n = all.len();
    let rps = if elapsed > 0.0 { n as f64 / elapsed } else { 0.0 };
    println!(
        "{{\"concurrency\":{},\"requests\":{},\"errors\":{},\"elapsed_s\":{:.6},\"rps\":{:.2},\"p50_us\":{:.1},\"p95_us\":{:.1},\"p99_us\":{:.1},\"mean_us\":{:.1}}}",
        concurrency,
        n,
        errors,
        elapsed,
        rps,
        pct(&all, 0.50) as f64 / 1000.0,
        pct(&all, 0.95) as f64 / 1000.0,
        pct(&all, 0.99) as f64 / 1000.0,
        if n > 0 { all.iter().sum::<u64>() as f64 / n as f64 / 1000.0 } else { 0.0 }
    );
}
