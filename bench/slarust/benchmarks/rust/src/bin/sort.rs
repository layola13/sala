fn main() {
    let n: i64 = 1_000_000;
    let mut v: Vec<i64> = Vec::new();
    let mut seed: i64 = 12345;
    let mut i: i64 = 0;
    while i < n {
        seed = (seed * 1_103_515_245 + 12345) % 2_147_483_648;
        v.push(seed);
        i += 1;
    }

    let mut start: i64 = n / 2 - 1;
    while start >= 0 {
        let mut root: i64 = start;
        let mut done: bool = false;
        while !done {
            let child: i64 = root * 2 + 1;
            if child > n - 1 {
                done = true;
            } else {
                let mut pick: i64 = root;
                if v[pick as usize] < v[child as usize] {
                    pick = child;
                }
                if child + 1 <= n - 1 && v[pick as usize] < v[(child + 1) as usize] {
                    pick = child + 1;
                }
                if pick != root {
                    v.swap(root as usize, pick as usize);
                    root = pick;
                } else {
                    done = true;
                }
            }
        }
        start -= 1;
    }

    let mut end: i64 = n - 1;
    while end > 0 {
        v.swap(0, end as usize);
        let mut root: i64 = 0;
        let mut done: bool = false;
        while !done {
            let child: i64 = root * 2 + 1;
            if child > end - 1 {
                done = true;
            } else {
                let mut pick: i64 = root;
                if v[pick as usize] < v[child as usize] {
                    pick = child;
                }
                if child + 1 <= end - 1 && v[pick as usize] < v[(child + 1) as usize] {
                    pick = child + 1;
                }
                if pick != root {
                    v.swap(root as usize, pick as usize);
                    root = pick;
                } else {
                    done = true;
                }
            }
        }
        end -= 1;
    }

    let mut checksum: i64 = 0;
    let mut j: i64 = 0;
    while j < n {
        checksum = (checksum * 31 + v[j as usize]) % 1_000_000_007;
        j += 1;
    }
    println!("{}", checksum);
}
