fn main() {
    let n: i64 = 32_000_000;
    let mut v: Vec<i64> = Vec::new();
    let mut i: i64 = 0;
    while i < n {
        v.push(i * 3 + 1);
        i += 1;
    }
    let mut checksum: i64 = 0;
    let mut j: i64 = 0;
    while j < n {
        checksum = (checksum + v[j as usize]) % 1_000_000_007;
        j += 1;
    }
    println!("{}", checksum);
}
