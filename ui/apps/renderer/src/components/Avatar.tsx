import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment } from "@react-three/drei";
import { useRef, useEffect, useState } from "react";
import * as THREE from "three";

interface AvatarProps {
  audioAnalyser?: AnalyserNode | null;
  isSpeaking?: boolean;
}

function NinjaModel({ audioAnalyser, isSpeaking }: AvatarProps) {
  const { scene, nodes, materials } = useGLTF("/ninja.glb");
  const groupRef = useRef<THREE.Group>(null);
  const mouthRef = useRef<THREE.Mesh | null>(null);
  const [mouthOpen, setMouthOpen] = useState(0);

  useEffect(() => {
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        if (child.name.toLowerCase().includes("mouth") || 
            child.name.toLowerCase().includes("jaw") ||
            child.name.toLowerCase().includes("lip")) {
          mouthRef.current = child;
        }
      }
    });
  }, [scene]);

  useFrame(() => {
    if (audioAnalyser && isSpeaking) {
      const dataArray = new Uint8Array(audioAnalyser.frequencyBinCount);
      audioAnalyser.getByteFrequencyData(dataArray);
      const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
      const target = Math.min(average / 128, 1) * 0.3;
      setMouthOpen(target);

      if (mouthRef.current) {
        mouthRef.current.scale.y = 1 + target;
      }
    } else {
      setMouthOpen(0);
      if (mouthRef.current) {
        mouthRef.current.scale.y = THREE.MathUtils.lerp(
          mouthRef.current.scale.y,
          1,
          0.1
        );
      }
    }

    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(Date.now() * 0.0005) * 0.1;
    }
  });

  return (
    <group ref={groupRef}>
      <primitive object={scene} scale={1.5} position={[0, -1, 0]} />
    </group>
  );
}

export function Avatar({ audioAnalyser, isSpeaking }: AvatarProps) {
  useEffect(() => {
    useGLTF.preload("/ninja.glb");
  }, []);

  return (
    <div className="avatar-container">
      <Canvas
        camera={{ position: [0, 0, 4], fov: 50 }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 5, 5]} intensity={1} />
        <pointLight position={[-5, 3, -5]} intensity={0.5} color="#8b5cf6" />
        <pointLight position={[5, -3, 5]} intensity={0.3} color="#3b82f6" />
        <NinjaModel audioAnalyser={audioAnalyser} isSpeaking={isSpeaking} />
        <OrbitControls enableZoom={false} enablePan={false} autoRotate={false} />
        <Environment preset="night" />
      </Canvas>
      <div className="avatar-status">
        <div className={`status-dot ${isSpeaking ? "speaking" : "idle"}`} />
        <span>{isSpeaking ? "Hablando" : "Escuchando"}</span>
      </div>
    </div>
  );
}
