# Parametric-Surface ASCII Renderer – Theory of Operation
#
# This note explains what the program draws, where the math lives, and why
# the implementation uses a uniform “radial × angular” grid.
#
# ---
#
# 1. Surfaces in ℝ³
#
# Every YAML file defines a smooth parametric map:
#
#   F(u, v) = (x(u, v), y(u, v), z(u, v))
#
# with parameters (u, v) in a rectangle domain D:
#
#   D = [u_min, u_max] × [v_min, v_max]
#
# The parametric patch is a flat rectangle in (u, v) even if the 3D surface
# curls around or self-intersects.
#
# Examples:
#
# | YAML          | Description                    | Domain                           | Topology           |
# |---------------|--------------------------------|----------------------------------|---------------------|
# | boy.yaml      | Souriau immersion of RP²       | u ∈ [0, π], v ∈ [0, 2π]          | Non-orientable     |
# | torus.yaml    | Standard torus                 | u, v ∈ [0, 2π]                   | Genus 1            |
# | horn.yaml     | Gabriel’s horn                 | u ∈ [1, 15], v ∈ [0, 2π]         | Infinite area      |
#
# ---
#
# 2. Uniform grid in parameter space
#
# We sample N₁ points along u and N₂ points along v:
#
#   uᵢ = u_min + ((i + 0.5)/N₁) × (u_max - u_min)
#   vⱼ = v_min + (j / N₂) × (v_max - v_min)
#
# where i = 0…N₁-1, j = 0…N₂-1.
#
# Notes:
# - The half-cell shift in u keeps points away from singularities at the boundary.
# - The grid is always rectangular.
# - The names “radial” and “angular” are for readability: in the torus they
#   do correspond to radial and angular directions, but for more general surfaces
#   they are just grid axes.
#
# ---
#
# 3. Normals
#
# In the Python version:
#   ∂F/∂u and ∂F/∂v are computed with symbolic differentiation (SymPy).
#
# In the Perl version:
#   Finite differences approximate the partial derivatives:
#
#     F_u ≈ [F(u + ε, v) - F(u, v)] / ε
#     F_v ≈ [F(u, v + ε) - F(u, v)] / ε
#
# The normal vector is the cross product:
#
#     N_raw = F_u × F_v
#
# It is then normalised to unit length:
#
#     N = N_raw / |N_raw|
#
# ---
#
# 4. From ℝ³ to terminal cells
#
# 1. **Rotation**
#    Two angles (horizontal and vertical) applied via Euler rotations:
#      - Rotate around Y axis (horizontal spin)
#      - Rotate around X axis (vertical tilt)
#
# 2. **Orthographic projection**
#      Discard z and scale (x, y) by the zoom factor.
#
# 3. **Mapping to grid**
#      Map (x_s, y_s) in [-1, +1] to (grid_x, grid_y):
#
#        grid_x = floor((x_s + 1) × 0.5 × (cols - 1))
#        grid_y = rows - 1 - floor((y_s + 1) × 0.5 × (rows - 1))
#
# 4. **Depth buffer**
#      For each cell, keep the highest z so closer surfaces overwrite farther ones.
#
# 5. **Lambertian shading**
#      Compute:
#
#        I_raw = max(0, N ⋅ L)
#        I = I_raw ^ gamma
#
#      where L is the light direction (normalized) and gamma ≈ 0.4.
#
# 6. **Quantisation**
#      Map I to:
#      - 12-glyph brightness gradient:
#        ".,-~:;=!*#$@"
#      - ANSI grayscale codes 232–255 for terminal colors.
#
#      Rounding (+0.5) ensures the brightest cell uses '@' and code 255.
#
# ---
#
# 5. Why this grid works
#
# - Uniform density makes aliasing predictable.
# - One sample per grid cell: no interpolation needed.
# - Complexity is O(N₁ × N₂) per frame.
# - For smooth surfaces, ~60×360 samples are sufficient.
# - Different YAML surfaces only change F(u, v) and its derivatives;
#   the grid and renderer stay the same.
#
# ---
#
# 6. Extending and tweaking
#
# - Increase radial/angular resolution for more detail.
# - Use adaptive ε for finite differences in high-curvature areas.
# - Replace orthographic projection with weak perspective:
#
#      (x_proj, y_proj) = (f / (f - z)) × (x, y)
#
# - Add multiple lights by summing contributions before quantising.
#
# ---
#
# Last updated: 2025-07-13
