use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

const RESPONSE: &[u8] =
    b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\nConnection: keep-alive\r\n\r\nok";

fn handle(mut stream: TcpStream) {
    let _ = stream.set_nodelay(true);
    let mut buf = [0u8; 8192];
    let mut used = 0usize;
    loop {
        let header_end = loop {
            if let Some(pos) = buf[..used]
                .windows(4)
                .position(|w| w == b"\r\n\r\n")
            {
                break pos + 4;
            }
            match stream.read(&mut buf[used..]) {
                Ok(0) => return,
                Ok(n) => used += n,
                Err(_) => return,
            }
            if used == buf.len() {
                return;
            }
        };
        if stream.write_all(RESPONSE).is_err() {
            return;
        }
        let rest = used - header_end;
        if rest > 0 {
            buf.copy_within(header_end..used, 0);
            used = rest;
        } else {
            used = 0;
        }
    }
}

fn main() {
    let addr = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "127.0.0.1:18093".to_string());
    let listener = TcpListener::bind(&addr).expect("bind");
    println!("listen {}", addr);
    for stream in listener.incoming() {
        match stream {
            Ok(stream) => {
                thread::spawn(move || handle(stream));
            }
            Err(_) => continue,
        }
    }
}
