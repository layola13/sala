fn main() {
    let n: i64 = 33_554_432;
    let mut data: Vec<u8> = Vec::new();
    let mut i: i64 = 0;
    while i < n {
        data.push((i % 251) as u8);
        i += 1;
    }
    let mut checksum: i64 = 0;
    let mut j: i64 = 0;
    while j < n {
        checksum = (checksum * 31 + data[j as usize] as i64) % 1_000_000_007;
        j += 64;
    }
    println!("{}", checksum);
}
