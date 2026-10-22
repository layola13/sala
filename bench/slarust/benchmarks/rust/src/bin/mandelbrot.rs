fn main() {
    let width: i64 = 1600;
    let height: i64 = 1600;
    let max_iter: i64 = 200;
    let mut count: i64 = 0;
    let mut py: i64 = 0;
    while py < height {
        let y0: f64 = (py as f64) * 2.0 / (height as f64) - 1.0;
        let mut px: i64 = 0;
        while px < width {
            let x0: f64 = (px as f64) * 3.5 / (width as f64) - 2.5;
            let mut x: f64 = 0.0;
            let mut y: f64 = 0.0;
            let mut it: i64 = 0;
            while it < max_iter {
                let x2 = x * x;
                let y2 = y * y;
                if x2 + y2 > 4.0 {
                    break;
                }
                let ny = 2.0 * x * y + y0;
                x = x2 - y2 + x0;
                y = ny;
                it += 1;
            }
            count += it;
            px += 1;
        }
        py += 1;
    }
    println!("{}", count);
}
