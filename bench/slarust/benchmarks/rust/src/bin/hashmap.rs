fn main() {
    let cap: i64 = 4_194_304;
    let n: i64 = 3_000_000;
    let mut keys: Vec<i64> = Vec::new();
    let mut vals: Vec<i64> = Vec::new();
    let mut i: i64 = 0;
    while i < cap {
        keys.push(-1);
        vals.push(0);
        i += 1;
    }

    let mut k: i64 = 0;
    while k < n {
        let mut idx: i64 = (k * 2_654_435_761) % cap;
        let mut placed: bool = false;
        while !placed {
            if keys[idx as usize] == -1 {
                keys[idx as usize] = k;
                vals[idx as usize] = k * 3 + 1;
                placed = true;
            } else if keys[idx as usize] == k {
                placed = true;
            } else {
                idx = (idx + 1) % cap;
            }
        }
        k += 1;
    }

    let mut checksum: i64 = 0;
    let mut q: i64 = 0;
    while q < n {
        let mut idx: i64 = (q * 2_654_435_761) % cap;
        let mut found: bool = false;
        while !found {
            if keys[idx as usize] == -1 {
                found = true;
            } else if keys[idx as usize] == q {
                checksum = (checksum + vals[idx as usize]) % 1_000_000_007;
                found = true;
            } else {
                idx = (idx + 1) % cap;
            }
        }
        q += 1;
    }
    println!("{}", checksum);
}
