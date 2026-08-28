// Vertex shader — passa as UVs
export const vertexShader = /* glsl */ `
  varying vec2 vUv;

  void main() {
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`

// Fragment shader — halftone de dots circulares
export const fragmentShader = /* glsl */ `
  uniform sampler2D uVideoTexture;
  uniform float uGridSize;
  uniform float uDotSize;
  uniform float uContrast;
  uniform float uBrightness;
  uniform float uEffectStrength;
  uniform vec3 uColor;
  uniform vec3 uBgColor;
  uniform float uTime;
  uniform vec2 uResolution;

  varying vec2 vUv;

  void main() {
    // 1. Pixeliza: amostra o centro da célula
    vec2 pixelSize = uGridSize / uResolution;
    vec2 cellUv    = floor(vUv / pixelSize) * pixelSize + pixelSize * 0.5;
    vec3 videoColor = texture2D(uVideoTexture, cellUv).rgb;

    // 2. Contraste e brilho
    vec3 color = (videoColor - 0.5) * uContrast + 0.5 + uBrightness;
    color = clamp(color, 0.0, 1.0);

    // 3. Halftone: dot cujo raio depende da luminância
    float lum    = dot(color, vec3(0.299, 0.587, 0.114));
    float radius = uDotSize * sqrt(lum);
    vec2  cell   = fract(vUv / pixelSize) - 0.5;
    float dotM   = smoothstep(radius + 0.02, radius - 0.02, length(cell));

    // 4. Mix: dots coloridos sobre o fundo (uBgColor)
    vec3 dotColor   = color * uColor * dotM;
    vec3 finalColor = mix(uBgColor, dotColor + uBgColor * (1.0 - dotM), dotM);

    gl_FragColor = vec4(finalColor, 1.0);
  }
`
