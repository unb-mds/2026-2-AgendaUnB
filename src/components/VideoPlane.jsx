import { useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { vertexShader, fragmentShader } from '../shaders/videoShader.js'

export default function VideoPlane({ videoTexture, settings }) {
  const materialRef = useRef()
  const { size } = useThree()

  useFrame((_, delta) => {
    const mat = materialRef.current
    if (!mat) return

    mat.uniforms.uGridSize.value        = settings.gridSize
    mat.uniforms.uDotSize.value         = settings.dotSize
    mat.uniforms.uContrast.value        = settings.contrast
    mat.uniforms.uBrightness.value      = settings.brightness
    mat.uniforms.uEffectStrength.value  = settings.effectStrength
    mat.uniforms.uColor.value.set(...settings.color)
    mat.uniforms.uBgColor.value.set(...settings.bgColor)
    mat.uniforms.uTime.value           += delta
    mat.uniforms.uResolution.value.set(size.width, size.height)
  })

  return (
    <mesh>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={materialRef}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        depthTest={false}
        depthWrite={false}
        uniforms={{
          uVideoTexture:  { value: videoTexture },
          uGridSize:      { value: settings.gridSize },
          uDotSize:       { value: settings.dotSize },
          uContrast:      { value: settings.contrast },
          uBrightness:    { value: settings.brightness },
          uEffectStrength:{ value: settings.effectStrength },
          uColor:         { value: new THREE.Color(...settings.color) },
          uBgColor:       { value: new THREE.Color(...settings.bgColor) },
          uTime:          { value: 0.0 },
          uResolution:    { value: new THREE.Vector2(size.width, size.height) },
        }}
      />
    </mesh>
  )
}
