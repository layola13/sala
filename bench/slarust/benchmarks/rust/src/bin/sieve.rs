fn main() {
    let n: i64 = 20_000_000;
    let mut flags: Vec<u8> = Vec::new();
    let mut i: i64 = 0;
    while i < n {
        flags.push(1);
        i += 1;
    }
    flags[0] = 0;
    flags[1] = 0;
    let mut p: i64 = 2;
    while p * p < n {
        if flags[p as usize] == 1 {
            let mut j: i64 = p * p;
            while j < n {
                flags[j as usize] = 0;
                j += p;
            }
        }
        p += 1;
    }
    let mut count: i64 = 0;
    let mut k: i64 = 0;
    while k < n {
        count += flags[k as usize] as i64;
        k += 1;
    }
    println!("{}", count);
}
