import cmath
import math
import time
import shutil
import sys
import signal
import argparse


import yaml, math
import sympy as sp

from pathlib import Path

# Donut-style brightness gradient
GRADIENT = '.,-~:;=!*#$@'
# ANSI grayscale range for 256-color: 232 (dark) to 255 (bright)
GS_MIN, GS_MAX = 232, 255
LIGHT_DIR = (0.0, 0.0, 1.0)


def load_surface_OLD(path):
    spec = yaml.safe_load(open(path))
    u, v = sp.symbols(spec['vars'])
    umin, umax = spec['domain']['u']
    θmin, θmax = spec['domain']['θ']

    # base namespace for sympify
    ns = {
        'u': u,
        'θ': v,
        'u_min': umin,
        'u_max': umax,
        'sin': sp.sin,
        'cos': sp.cos,
        'pi': sp.pi,
        # basic math ops
    }

    # collect only real lines, skip comments
    raw = spec['equations'].splitlines()
    lines = [l.strip() for l in raw if l.strip() and not l.strip().startswith('#')]

    # sequentially sympify each assignment into ns
    for line in lines:
        name, expr = [part.strip() for part in line.split('=', 1)]
        ns[name] = sp.sympify(expr, locals=ns)

    # extract the final x,y,z symbols
    x_s = ns.get('x')
    y_s = ns.get('y')
    z_s = ns.get('z')
    if not all((x_s, y_s, z_s)):
        raise ValueError("`equations` must define x, y, and z.")

    # compute partial derivatives for normals
    xu, xv = sp.diff(x_s, u), sp.diff(x_s, v)
    yu, yv = sp.diff(y_s, u), sp.diff(y_s, v)
    zu, zv = sp.diff(z_s, u), sp.diff(z_s, v)

    # lambdify
    f_xyz = sp.lambdify((u, v), (x_s, y_s, z_s), 'math')
    f_du = sp.lambdify((u, v), (xu, yu, zu), 'math')
    f_dv = sp.lambdify((u, v), (xv, yv, zv), 'math')

    def point(a, b):
        return f_xyz(a, b)

    def normal(a, b):
        ax, ay, az = f_du(a, b)
        bx, by, bz = f_dv(a, b)
        nx, ny, nz = (
            ay * bz - az * by,
            az * bx - ax * bz,
            ax * by - ay * bx,
        )
        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        return (nx / L, ny / L, nz / L)

    def ranges():
        return (umin, umax, θmin, θmax)

    return point, normal, ranges


def load_surface(path):
    spec = yaml.safe_load(open(path))
    u, v = sp.symbols(spec['vars'])

    umin = sp.sympify(spec['domain']['u'][0], locals={'pi': sp.pi})
    umax = sp.sympify(spec['domain']['u'][1], locals={'pi': sp.pi})
    θmin = sp.sympify(spec['domain']['θ'][0], locals={'pi': sp.pi})
    θmax = sp.sympify(spec['domain']['θ'][1], locals={'pi': sp.pi})

    umin = float(umin)
    umax = float(umax)
    θmin = float(θmin)
    θmax = float(θmax)

    # base namespace for sympify
    ns = {
        'u': u,
        'θ': v,
        'u_min': umin,
        'u_max': umax,
        'sin': sp.sin,
        'cos': sp.cos,
        'pi': sp.pi,
        # basic math ops
    }

    # collect only real lines, skip comments
    raw = spec['equations'].splitlines()
    lines = [l.strip() for l in raw if l.strip() and not l.strip().startswith('#')]

    # sequentially sympify each assignment into ns
    for line in lines:
        name, expr = [part.strip() for part in line.split('=', 1)]
        ns[name] = sp.sympify(expr, locals=ns)

    # extract the final x,y,z symbols
    x_s = ns.get('x')
    y_s = ns.get('y')
    z_s = ns.get('z')
    if not all((x_s, y_s, z_s)):
        raise ValueError("`equations` must define x, y, and z.")

    # compute partial derivatives for normals
    xu, xv = sp.diff(x_s, u), sp.diff(x_s, v)
    yu, yv = sp.diff(y_s, u), sp.diff(y_s, v)
    zu, zv = sp.diff(z_s, u), sp.diff(z_s, v)

    # lambdify
    f_xyz = sp.lambdify((u, v), (x_s, y_s, z_s), 'math')
    f_du = sp.lambdify((u, v), (xu, yu, zu), 'math')
    f_dv = sp.lambdify((u, v), (xv, yv, zv), 'math')

    def point(a, b):
        return f_xyz(a, b)

    def normal(a, b):
        ax, ay, az = f_du(a, b)
        bx, by, bz = f_dv(a, b)
        nx, ny, nz = (
            ay * bz - az * by,
            az * bx - ax * bz,
            ax * by - ay * bx,
        )
        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        return (nx / L, ny / L, nz / L)

    def ranges():
        return (umin, umax, θmin, θmax)

    return point, normal, ranges


def build_mesh(loader, radial, angular):
    point, normal, rng = loader
    u0, u1, v0, v1 = rng() if callable(rng) else rng
    mesh = []
    for i in range(radial):
        u = u0 + (i + 0.5) / radial * (u1 - u0)
        for j in range(angular):
            v = v0 + j / angular * (v1 - v0)
            mesh.append((point(u, v), normal(u, v)))
    return mesh


def rotate_x(p, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    return (x, c * y - s * z, s * y + c * z)


def rotate_y(p, a):
    c, s = math.cos(a), math.sin(a)
    x, y, z = p
    return (c * x + s * z, y, -s * x + c * z)


def shade_char(intensity, use_color):
    idx = min(int(intensity * (len(GRADIENT) - 1)), len(GRADIENT) - 1)
    char = GRADIENT[idx]
    if use_color and intensity >= 0:
        code = GS_MIN + int(intensity * (GS_MAX - GS_MIN))
        return f'\x1b[38;5;{code}m{char}\x1b[0m'
    return char


def render(mesh, cols, rows, ah, av, zoom, use_color):
    depth = [[-1e9] * cols for _ in range(rows)]
    frame = [[' '] * cols for _ in range(rows)]
    for (px, py, pz), normal in mesh:
        p1 = rotate_x(rotate_y((px, py, pz), ah), av)
        n1 = rotate_x(rotate_y(normal, ah), av)
        xs, ys, zs = p1[0] * zoom, p1[1] * zoom, p1[2] * zoom
        gx = int((xs + 1) * 0.5 * (cols - 1))
        gy = rows - 1 - int((ys + 1) * 0.5 * (rows - 1))
        if 0 <= gx < cols and 0 <= gy < rows and zs > depth[gy][gx]:
            depth[gy][gx] = zs
            intensity = max(
                0.0, n1[0] * LIGHT_DIR[0] + n1[1] * LIGHT_DIR[1] + n1[2] * LIGHT_DIR[2]
            )
            # gamma boost
            intensity = math.sqrt(intensity)
            frame[gy][gx] = shade_char(intensity, use_color)
    sys.stdout.write('\033[H')
    for row in frame:
        sys.stdout.write(''.join(row) + '\n')
    sys.stdout.flush()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--zoom', type=float, default=1.0)
    p.add_argument('--radial', type=int, default=30)
    p.add_argument('--angular', type=int, default=180)
    p.add_argument('--speed', type=float, default=0.5)
    p.add_argument('--vspeed', type=float)
    p.add_argument('--no-color', action='store_true')
    p.add_argument('--shape-dir', type=str, default='shapes')
    p.add_argument('--shape', type=str, default='boy.yaml')
    args = p.parse_args()

    vs = args.vspeed if args.vspeed is not None else args.speed
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    cols, rows = shutil.get_terminal_size()
    cols -= 2
    rows -= 2

    shape_path = Path(args.shape_dir, args.shape)
    point_fn, normal_fn, ranges_fn = load_surface(shape_path)
    domain = ranges_fn()
    mesh = build_mesh((point_fn, normal_fn, domain), args.radial, args.angular)

    t0 = time.time()
    sys.stdout.write('\033[?25l')
    try:
        while True:
            t = time.time() - t0
            render(mesh, cols, rows, t * args.speed, t * vs, args.zoom, not args.no_color)
            time.sleep(0.03)
    finally:
        sys.stdout.write('\033[?25h')
        sys.stdout.write('\n')


if __name__ == '__main__':
    main()
