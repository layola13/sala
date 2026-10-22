fn main() {
    let n: i64 = 300_000_000;
    let mut acc: i64 = 0;
    let mut i: i64 = 0;
    while i < n {
        acc += (i % 7) * (i % 11);
        i += 1;
    }
    println!("{}", acc);
}
