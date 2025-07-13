# Parametric-Surface ASCII Renderer – Theory of Operation  
 
This note explains *what* our program draws, *where* the math lives, and *why* the  
implementation chooses a uniform “radial × angular” grid.  
 
---  
## 1 Surfaces in ℝ³  
Every YAML file defines a smooth **parametric map**  
\[  
  \mathbf F(u,v)=\bigl(x(u,v),\,y(u,v),\,z(u,v)\bigr),  
  \qquad (u,v)\in\mathcal D  
\]  
* **Target space**  \( \mathbb R^{3} \).  
* **Parameter space**  \( \mathcal D=[u_{\min},u_{\max}]\times[v_{\min},v_{\max}]  
  \subset\mathbb R^{2} \).  
  The parametric patch is a *flat rectangle* even when the surface in 3-D curls or self-intersects.  
 
| YAML example | Mathematical identity | Domain \(\mathcal D\) | Topology hint |  
|-------------|-----------------------|-----------------------|---------------|  
| `boy.yaml`    | Souriau immersion of \( \mathbb{RP}^2 \) | \(u\!:\!0\to\pi,\;v\!:\!0\to2\pi\) | non-orientable |  
| `torus.yaml`  | Standard donut       | \(u,v:0\to2\pi\)     | genus 1       |  
| `horn.yaml`   | Gabriel’s horn       | \(u\!:\!1\to15,\;v:0\to2\pi\) | infinite volume |  
 
---  
## 2 Uniform grid in parameter space  
We sample \(N_u=\mathtt{radial}\) points along \(u\) and \(N_v=\mathtt{angular}\) points along \(v\).  
\[
  u_i=u_{\min}+\Bigl(\tfrac{i+\tfrac12}{N_u}\Bigr)(u_{\max}-u_{\min}),\quad
  v_j=v_{\min}+\Bigl(\tfrac{j}{N_v}\Bigr)(v_{\max}-v_{\min}),
  \;i=0..N_u\!-\!1,\;j=0..N_v\!-\!1
\]  
* **Half-cell shift** on \(u\) keeps us away from boundary singularities.  
* The grid is rectangular; “radial / angular” are just human-friendly names matching the usual interpretation for tori, spheres, Boy surface, etc.  
 
---  
## 3 Normals  
*Analytic path (Python)* – `sympy.diff` yields  
\(\mathbf F_u,\mathbf F_v\).  
*Finite-difference path (Perl)* –  
\[
  \mathbf F_u \approx \frac{\mathbf F(u+\varepsilon,v)-\mathbf F(u,v)}{\varepsilon},\qquad
  \mathbf F_v \approx \frac{\mathbf F(u,v+\varepsilon)-\mathbf F(u,v)}{\varepsilon}
\]  
Unit normal  
\( \mathbf N=\dfrac{\mathbf F_u\times\mathbf F_v}{\lVert\mathbf F_u\times\mathbf F_v\rVert}. \)  
 
---  
## 4 From ℝ³ to terminal cells  
1. **Rigid rotation** – two Euler angles  
   \(R_y(\alpha_h)\,R_x(\alpha_v)\).  
2. **Orthographic projection** – drop \(z\), scale by `zoom`.  
3. **Screen mapping** –  
   \((x_s,y_s)\in[-1,1]^2 \to (g_x,g_y)\in[0,\text{cols}-1]\times[0,\text{rows}-1]\).  
4. **Depth buffer** – keep the largest \(z_s\) per cell.  
5. **Lambertian shade** –  
   \(I=\max(0,\,\mathbf N\!\cdot\!\mathbf L)^{\gamma}\).  
6. **Quantise** – map \(I\) to 12-glyph gradient `.,-~:;=!*#$@` and 24 ANSI greys (`232…255`) using rounding (+0.5) so brightest dot reaches glyph ‘@’ and colour 255.  
 
---  
## 5 Why this grid is sufficient  
* **Uniform density** keeps aliasing predictable.  
* One sample → one cell ⇒ \(O(N_uN_v)\) work, no interpolation.  
* For smooth surfaces the Nyquist rate is modest; Boy surface looks good at 60×360.  
* All surfaces share the grid logic; only \(\mathbf F\) and its derivatives differ.  
 
---  
## 6 Extending / tweaking  
* Increase `radial`,`angular` → finer surface detail (CPU cost ∝ grid size).  
* Use adaptive ε in finite differences to stabilise high-curvature regions.  
* Swap orthographic for weak-perspective:  
  \( (x_s,y_s) = \dfrac{f}{f-z}\,(x,y) \).  
* Multi-light: accumulate several \(I_k\) before quantising.  
 
---  
*Last updated 2025-07-13*
