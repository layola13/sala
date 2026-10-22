fn main() {
    let n: i64 = 64;
    let elems: i64 = 4096;
    let reps: i64 = 4000;
    let a: [f64; 4096] = [1.5; 4096];
    let b: [f64; 4096] = [2.0; 4096];
    let mut c: [f64; 4096] = [0.0; 4096];
    let mut total: f64 = 0.0;
    let mut rep: i64 = 0;
    while rep < reps {
        let mut r: i64 = 0;
        while r < n {
            let mut col: i64 = 0;
            while col < n {
                let mut acc: f64 = 0.0;
                let mut k: i64 = 0;
                while k < n {
                    acc += a[(r * n + k) as usize] * b[(k * n + col) as usize];
                    k += 1;
                }
                c[(r * n + col) as usize] = acc;
                col += 1;
            }
            r += 1;
        }
        let mut j: i64 = 0;
        while j < elems {
            total += c[j as usize];
            j += 1;
        }
        rep += 1;
    }
    println!("{}", total as i64);
}
