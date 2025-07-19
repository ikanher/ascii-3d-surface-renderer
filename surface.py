import argparse
import math
import shutil
import signal
import sys
import time
from pathlib import Path

import sympy as sp
import yaml

# Donut-style brightness gradient
GRADIENT = '.,-~:;=!*#$@'

# ANSI grayscale range for 256-color: 232 (dark) to 255 (bright)
GS_MIN, GS_MAX = 232, 255  # full ANSI grayscale ramp
DELAY = 0.01

# Light direction will be overrider from CLI
LIGHT_DIR = (1 / math.sqrt(2), 1 / math.sqrt(2), 0)


def load_surface(path):
    spec = yaml.safe_load(open(path))
    var_names = spec['vars']
    if len(var_names) != 2:
        raise ValueError('Exactly two parameters are required.')

    # Read optional normal sign
    normal_sign = spec.get('normal_sign', 1)
    if normal_sign not in (-1, 1):
        raise ValueError('normal_sign must be -1 or 1')

    # Make symbols
    symbols = [sp.Symbol(name) for name in var_names]
    var_a, var_b = symbols
    name_a, name_b = var_names

    # Sympify domain bounds
    domain_locals = {'pi': sp.pi, 'PI': sp.pi}
    dom_a = [float(sp.sympify(x, locals=domain_locals)) for x in spec['domain'][name_a]]
    dom_b = [float(sp.sympify(x, locals=domain_locals)) for x in spec['domain'][name_b]]

    # Build sympify namespace
    ns = {
        name_a: var_a,
        name_b: var_b,
        'sin': sp.sin,
        'cos': sp.cos,
        'tan': sp.tan,
        'atan2': sp.atan2,
        'sqrt': sp.sqrt,
        'pi': sp.pi,
        'acos': sp.acos,
        f'{name_a}_min': dom_a[0],
        f'{name_a}_max': dom_a[1],
        f'{name_b}_min': dom_b[0],
        f'{name_b}_max': dom_b[1],
    }

    # Collect equation lines
    raw = spec['equations'].splitlines()
    lines = [l.strip() for l in raw if l.strip() and not l.strip().startswith('#')]

    # Evaluate assignments
    for line in lines:
        name, expr = [part.strip() for part in line.split('=', 1)]
        ns[name] = sp.sympify(expr, locals=ns)

    # Final coordinates
    x_s = ns.get('x')
    y_s = ns.get('y')
    z_s = ns.get('z')
    if not all((x_s, y_s, z_s)):
        raise ValueError('`equations` must define x, y, z.')

    # Derivatives
    xu, xv = sp.diff(x_s, var_a), sp.diff(x_s, var_b)
    yu, yv = sp.diff(y_s, var_a), sp.diff(y_s, var_b)
    zu, zv = sp.diff(z_s, var_a), sp.diff(z_s, var_b)

    # Lambdify, allowing partial-derivative nodes in the generated code
    from sympy.printing.pycode import PythonCodePrinter

    printer = PythonCodePrinter({'strict': False})
    f_xyz = sp.lambdify((var_a, var_b), (x_s, y_s, z_s), 'math', printer=printer)
    f_du = sp.lambdify((var_a, var_b), (xu, yu, zu), 'math', printer=printer)
    f_dv = sp.lambdify((var_a, var_b), (xv, yv, zv), 'math', printer=printer)

    # Inject missing helpers into the generated functions' global namespaces
    helpers = {
        'math': math,
        're': lambda z: z,  # real part (our inputs are real)
        'im': lambda z: 0.0,  # imaginary part → always 0 here
        'sign': lambda x: (x > 0) - (x < 0),  # used by d/dx Abs(x)
    }

    for fn in (f_xyz, f_du, f_dv):
        fn.__globals__.update(helpers)

    def point(a, b):
        return f_xyz(a, b)

    def normal(a, b):
        ax, ay, az = f_du(a, b)
        bx, by, bz = f_dv(a, b)

        nx, ny, nz = (
            by * az - bz * ay,
            bz * ax - bx * az,
            bx * ay - by * ax,
        )

        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0

        return (normal_sign * nx / L, normal_sign * ny / L, normal_sign * nz / L)

    def ranges():
        return (*dom_a, *dom_b)

    return point, normal, ranges


def build_mesh(loader, radial, angular):
    point, normal, rng = loader
    u0, u1, v0, v1 = rng() if callable(rng) else rng
    mesh = []
    for i in range(radial):
        u = u0 + (i + 0.5) / radial * (u1 - u0)
        for j in range(angular):
            v = v0 + j / angular * (v1 - v0)
            try:
                P = point(u, v)
                N = normal(u, v)
            except (ValueError, ZeroDivisionError):  # math domain / singularities
                continue
            if not all(math.isfinite(c) for c in (*P, *N)):
                continue
            mesh.append((P, N))
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
    idx = round(intensity * (len(GRADIENT) - 1))
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
            intensity = max(0.0, n1[0] * LIGHT_DIR[0] + n1[1] * LIGHT_DIR[1] + n1[2] * LIGHT_DIR[2])
            # gamma boost
            # intensity = math.sqrt(intensity)
            intensity **= 0.4
            frame[gy][gx] = shade_char(intensity, use_color)
    sys.stdout.write('\033[H')
    for row in frame:
        sys.stdout.write(''.join(row) + '\n')
    sys.stdout.flush()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--light', default='1,1,0', help='comma separated XYZ for light direction')
    p.add_argument(
        '--orbit-light', action='store_true', help='orbit the light instead of rotating the object'
    )
    p.add_argument('--zoom', type=float, default=0.5)
    p.add_argument('--radial', type=int, default=120)
    p.add_argument('--angular', type=int, default=720)
    p.add_argument('--speed', type=float, default=0.5)
    p.add_argument('--vspeed', type=float)
    p.add_argument('--no-color', action='store_true')
    p.add_argument('--shape-path', type=str, default='shapes/torus.yaml')
    args = p.parse_args()

    # Light direction is a global variable
    global LIGHT_DIR

    vs = args.vspeed if args.vspeed is not None else args.speed
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    cols, rows = shutil.get_terminal_size()
    cols -= 2
    rows -= 2

    lx, ly, lz = map(float, args.light.split(','))
    L = math.sqrt(lx * lx + ly * ly + lz * lz) or 1.0

    # Set the light direction global variable
    LIGHT_DIR = (lx / L, ly / L, lz / L)

    shape_path = Path(args.shape_path)
    point_fn, normal_fn, ranges_fn = load_surface(shape_path)
    domain = ranges_fn()
    mesh = build_mesh((point_fn, normal_fn, domain), args.radial, args.angular)

    t0 = time.time()
    sys.stdout.write('\033[?25l')
    try:
        if args.orbit_light:
            ω = args.speed
            while True:
                t = time.time() - t0

                # polar-orbiting light (XZ plane)
                lx = math.cos(ω * t)
                ly = 0.9  # elevate the light
                lz = math.sin(ω * t)
                L = math.sqrt(lx * lx + ly * ly + lz * lz)

                LIGHT_DIR = (lx / L, ly / L, lz / L)

                render(
                    mesh,
                    cols,
                    rows,
                    0.0,
                    0.0,
                    args.zoom,
                    not args.no_color,  # keep object static
                )

                time.sleep(DELAY)
        else:
            while True:
                t = time.time() - t0
                render(mesh, cols, rows, t * args.speed, t * vs, args.zoom, not args.no_color)
                time.sleep(DELAY)
    finally:
        sys.stdout.write('\033[?25h')
        sys.stdout.write('\n')


if __name__ == '__main__':
    main()
