fn newton_sqrt(x: f64) -> f64 {
    let mut g: f64 = x;
    let mut i: i64 = 0;
    while i < 20 {
        g = 0.5 * (g + x / g);
        i += 1;
    }
    g
}

fn main() {
    let bodies: usize = 5;
    let steps: i64 = 1_000_000;
    let dt: f64 = 0.01;
    let mass: [f64; 5] = [1.0, 0.9, 0.8, 0.7, 0.6];
    let mut x: [f64; 5] = [0.0, 4.84, 8.34, 12.5, -3.0];
    let mut y: [f64; 5] = [0.0, 2.0, -1.5, 3.0, 5.0];
    let mut z: [f64; 5] = [0.0, 1.0, 2.0, -2.0, 0.5];
    let mut vx: [f64; 5] = [0.0, -0.1, 0.2, -0.2, 0.1];
    let mut vy: [f64; 5] = [0.0, 0.2, -0.1, 0.15, -0.05];
    let mut vz: [f64; 5] = [0.0, 0.05, -0.1, 0.05, 0.02];

    let mut step: i64 = 0;
    while step < steps {
        for i in 0..bodies {
            for j in (i + 1)..bodies {
                let dx = x[i] - x[j];
                let dy = y[i] - y[j];
                let dz = z[i] - z[j];
                let r2 = dx * dx + dy * dy + dz * dz;
                let inv = dt / (newton_sqrt(r2) * r2);
                vx[i] -= dx * mass[j] * inv;
                vy[i] -= dy * mass[j] * inv;
                vz[i] -= dz * mass[j] * inv;
                vx[j] += dx * mass[i] * inv;
                vy[j] += dy * mass[i] * inv;
                vz[j] += dz * mass[i] * inv;
            }
        }
        for b in 0..bodies {
            x[b] += dt * vx[b];
            y[b] += dt * vy[b];
            z[b] += dt * vz[b];
        }
        step += 1;
    }

    let mut energy: f64 = 0.0;
    for p in 0..bodies {
        energy += 0.5 * mass[p] * (vx[p] * vx[p] + vy[p] * vy[p] + vz[p] * vz[p]);
        for q in (p + 1)..bodies {
            let dx = x[p] - x[q];
            let dy = y[p] - y[q];
            let dz = z[p] - z[q];
            energy -= mass[p] * mass[q] / newton_sqrt(dx * dx + dy * dy + dz * dz);
        }
    }
    println!("{}", (energy * 1_000_000.0) as i64);
}
