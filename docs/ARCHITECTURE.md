# ARCHITECTURE.md

A concise yet complete overview of the ASCII-surface renderer.

```
YAML → SymPy (symbolic) → Mesh (points + normals) → Transform + shade → ASCII frame
```

---

## 1  `load_surface(path)`

### Purpose
Transform a **declarative** surface specification into **imperative** Python call-ables.

*Surface definition*

```
𝐅(u,v) = ⟨x(u,v), y(u,v), z(u,v)⟩ ,  (u,v) ∈ [u₀,u₁] × [v₀,v₁]
```

### Detailed steps

1. **YAML parsing**  ⇢  extract `vars`, `domain`, `equations`.
2. **Symbol creation**  ⇢  `u, v = sp.symbols(...)`.
3. **Namespace build**  ⇢  inject math functions (`sin`, `cos`, `sqrt`, …) and domain constants
   (`u_min`, `u_max`, …).
4. **Expression evaluation**  ⇢  each line `name = expr` is `sympify`’d into the namespace.
5. **Normals**

   ```
   𝐅ᵤ = ∂𝐅/∂u     𝐅ᵥ = ∂𝐅/∂v
   𝐍′ = 𝐅ᵤ × 𝐅ᵥ
   𝐍  = 𝐍′ / ‖𝐍′‖         ( unit normal )
   ```

6. **Compilation**  ⇢  `lambdify` three fast functions:
   - `f_xyz(u,v)` → (x,y,z)
   - `f_du(u,v)`  → 𝐅ᵤ
   - `f_dv(u,v)`  → 𝐅ᵥ
7. **Helper injection**  ⇢  tiny lambdas for `re`, `im`, `sign`, plus `math` module.

**Return**

```python
point(u,v)   → (x,y,z)
normal(u,v)  → (nx,ny,nz)
ranges()     → (u₀,u₁,v₀,v₁)
```

---

## 2  `build_mesh(loader, radial, angular)`

### Sampling grid

```
uᵢ = u₀ + (i + 0.5)/radial  · (u₁ − u₀)      i = 0 … radial−1
vⱼ = v₀ +  j       /angular · (v₁ − v₀)      j = 0 … angular−1
```

For each (uᵢ,vⱼ):

1. **Point / normal**  `P = point(uᵢ,vⱼ)`, `N = normal(uᵢ,vⱼ)`.
2. **Validation**      skip on exception, NaN, or ±∞.

Result:

```python
mesh = [((Px,Py,Pz), (Nx,Ny,Nz)), ...]
```

---

## 3  Realtime rendering

### 3.1 Rotation (object-space)

```
𝐏′ = Rₓ(α_v) · Rᵧ(α_h) · 𝐏
𝐍′ = Rₓ(α_v) · Rᵧ(α_h) · 𝐍
```

Simple 3 × 3 matrices; Z axis points **out of the screen**.

### 3.2 Orthographic projection

```
xₛ = zoom · Px′
yₛ = zoom · Py′
```

Map to terminal grid **[0, cols-1] × [0, rows-1]**

```
gₓ = ⌊ (xₛ+1)/2 · (cols−1) ⌋
gᵧ = rows−1 − ⌊ (yₛ+1)/2 · (rows−1) ⌋
```

### 3.3 Lambertian shading

**Lambertian** = *ideal diffuse reflection* ⇒ brightness ∝ cos θ  
(θ = angle between surface normal and light).

```
I₀ = max(0, 𝐍′ · 𝐋)        # dot product
I  = I₀^γ ,  γ ≈ 0.4       # perceptual gamma curve
```

γ=0.4 approximates sRGB inverse-gamma; feel free to tweak with `--gamma`.

### 3.4 ASCII/ANSI mapping

```
index = round(I · (len(GRADIENT)−1))
char  = GRADIENT[index]
color = 232 + I·(255−232)         # 24-step ANSI grayscale
```

### 3.5 Z-buffer

Store the deepest z per cell. Update only if new z is closer.

### 3.6 Flush

* `\033[H`  – cursor home  
* Print each row → `stdout`

---

## 4  Light vs. Object motion

**Object rotation (default)**

```
α_h = ω t
α_v = ω_v t
𝐋   = constant
```

**Light orbit (`--orbit-light`)**

```
α_h = α_v = 0
𝐋(t) = (cos ωt, 0.4, sin ωt)      # slight Y elevation
```

Both modes share the same rendering code.

---

## 5  Glyphs, Gamma & Palette

* **Gradient:** `.,-~:;=!*#$@`
* **Gamma:** 0.4 (expose via `--gamma` if desired)
* **ANSI greyscale:** 232 – 255 (24 shades)

---

## 6  Performance

| Stage          | Complexity               | Notes                         |
| -------------- | ------------------------ | ----------------------------- |
| Mesh build     | O(radial × angular)      | once at startup               |
| Per-frame math | O(|mesh|)                | ≈ rotations + dot products    |
| Terminal I/O   | O(cols × rows)           | stdout flush dominates large screens |

On a 160×50 terminal with 60×360 samples (~21 k points) the program sustains >30 fps on modest CPUs.

---

## 7  Extensibility

* **New shape:** drop a YAML file in `shapes/`.
* **Perspective:** replace orthographic mapping with  
  `xₛ = f·Px′/(d − Pz′)`, `yₛ` analogous.
* **Interactivity:** read non-blocking `stdin` to tweak speed, zoom, gamma.
* **Multiple lights / colour:** compute Σ Iᵢ and map to 24-bit ANSI.

---

*Last updated: 2025-07-12*
