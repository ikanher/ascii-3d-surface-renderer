# YAML Surface Specification

## YAML Surface Specification

Each surface is described in a YAML file with the following structure:

```yaml
Surface definition
vars: [u, v]
domain:
  u: [u_min, u_max]
  v: [v_min, v_max]
equations: |
  # Any number of helper assignments or comments
  # Format: name = expression
  # Must end with definitions for x, y, and z

  # Example helpers
  A = sin(u) * cos(v)
  B = u**2 + v**2

  # Final coordinates
  x = A / (1 + B)
  y = u * cos(v)
  z = u * sin(v)
```

### Keys

- **vars**
  A list of exactly two parameter names (e.g., ["u", "θ"]).
  These names will be used as symbols in the equations.

- **domain**
  A mapping from each parameter name to a two-element list defining its range:
  ```yaml
  domain:
    u: [0.0, 1.0]
    θ: [0.0, 6.283185307179586]
  ```

- **equations**
  A block containing:
  - Optional comments (lines starting with #)
  - Any number of helper assignments (name = expression)
  - Three final assignments defining x, y, and z

### Expressions

- Expressions can use:
  - The variables declared in vars
  - u_min, u_max, v_min, v_max for domain constants
  - Standard functions: sin(), cos(), tan(), exponentiation **
  - Numeric literals
- All expressions must be valid Python syntax parsable by SymPy.

### Requirements

- x, y, and z **must** be assigned in the equations block.
- All helper variables must be defined before they are referenced.

### Example

Gabriel’s Horn:

```yaml
vars: [u, θ]
domain:
  u: [1.0, 15.0]
  θ: [0.0, 6.283185307179586]
equations: |
  x = (u - (u_max + u_min)/2) / ((u_max - u_min)/2)
  y = cos(θ) / u
  z = sin(θ) / u
```
