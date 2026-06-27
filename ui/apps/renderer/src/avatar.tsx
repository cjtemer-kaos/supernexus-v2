import React from "react";
import ReactDOM from "react-dom/client";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, useGLTF, Environment } from "@react-three/drei";
import { useRef, useEffect, useState } from "react";
import * as THREE from "three";

function NinjaModel({ isTalking }: { isTalking: boolean }) {
  const gltf = useGLTF("/ninja.glb");
  const scene = gltf.scene;
  const groupRef = useRef<THREE.Group>(null);
  const mouthRef = useRef<THREE.Mesh | null>(null);

  useEffect(() => {
    console.log("NinjaModel: gltf loaded", { scene: !!scene, gltf });
  }, [scene]);

  useEffect(() => {
    if (scene) {
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          const name = child.name.toLowerCase();
          if (name.includes("mouth") || name.includes("jaw") || name.includes("lip")) {
            mouthRef.current = child;
          }
        }
      });
    }
  }, [scene]);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime) * 0.1;
    }
    if (mouthRef.current && isTalking) {
      mouthRef.current.scale.y = 1 + Math.sin(state.clock.elapsedTime * 15) * 0.4;
    } else if (mouthRef.current) {
      mouthRef.current.scale.y = THREE.MathUtils.lerp(mouthRef.current.scale.y, 1, 0.1);
    }
  });

  if (!scene) {
    console.warn("NinjaModel: scene not loaded, returning fallback");
    return <FallbackBox />;
  }

  return (
    <group ref={groupRef}>
      <primitive object={scene} scale={1.8} position={[0, -1.2, 0]} />
    </group>
  );
}

function FallbackBox() {
  return (
    <mesh position={[0, 0, 0]}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="#8b5cf6" wireframe />
    </mesh>
  );
}

function AvatarViewer() {
  const [isListening, setIsListening] = useState(false);
  const [isTalking, setIsTalking] = useState(false);
  const [status, setStatus] = useState("Listo");
  const [personality, setPersonality] = useState("director");
  const [personalities, setPersonalities] = useState<string[]>([]);
  const [showSelector, setShowSelector] = useState(false);

  useEffect(() => {
    useGLTF.preload("/ninja.glb");
    loadVoiceStatus();
  }, []);

  const loadVoiceStatus = async () => {
    try {
      const statusData = await window.nexusAPI.voiceStatus();
      if (statusData.personalities) {
        setPersonalities(statusData.personalities);
      }
      if (statusData.personality) {
        setPersonality(statusData.personality);
      }
    } catch (error) {
      console.error("Error loading voice status:", error);
    }
  };

  const changePersonality = async (newPersonality: string) => {
    try {
      const result = await window.nexusAPI.voiceSetPersonality(newPersonality);
      if (result.success) {
        setPersonality(newPersonality);
        setStatus(`Personalidad: ${newPersonality}`);
        setTimeout(() => setStatus("SISTEMA ACTIVO"), 2000);
      }
    } catch (error) {
      console.error("Error changing personality:", error);
    }
  };

  const processVoiceCommand = async () => {
    try {
      setStatus("Escuchando...");
      const listenResult = await window.nexusAPI.voiceListen(5);
      
      if (listenResult && listenResult.text && listenResult.text.trim()) {
        setStatus("Pensando...");
        const chatResult = await window.nexusAPI.chat(listenResult.text, "auto", "default");
        const reply = chatResult.content;
        
        if (reply) {
          setStatus("Hablando...");
          setIsTalking(true);
          await window.nexusAPI.voiceSpeak(reply);
          setIsTalking(false);
          setStatus("SISTEMA ACTIVO");
        } else {
          setStatus("SISTEMA ACTIVO");
        }
      } else {
        setStatus("SISTEMA ACTIVO");
      }
    } catch (error) {
      console.error("Error en proceso de voz:", error);
      setStatus("Error");
      setTimeout(() => setStatus("Listo"), 2000);
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" && !e.repeat && !isTalking && !isListening) {
        e.preventDefault();
        setIsListening(true);
      }
    };
    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        if (isListening) {
          setIsListening(false);
          processVoiceCommand();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [isListening, isTalking]);

  useEffect(() => {
    const dot = document.getElementById("status-dot");
    const text = document.getElementById("status-text");
    if (dot && text) {
      text.textContent = status === "Listo" ? "SISTEMA ACTIVO" : status;
      if (isListening || isTalking) {
        dot.classList.add("speaking");
      } else {
        dot.classList.remove("speaking");
      }
      
      if (status === "Escuchando...") dot.style.background = "#f97316";
      else if (status === "Pensando...") dot.style.background = "#3b82f6";
      else if (status === "Hablando...") dot.style.background = "#22c55e";
      else if (status === "Error") dot.style.background = "#ef4444";
      else dot.style.background = "#8b5cf6";
    }
  }, [isListening, isTalking, status]);

  return (
    <div style={{ position: "relative", width: "100vw", height: "100vh" }}>
      <Canvas camera={{ position: [0, 0, 3.5], fov: 45 }}>
        <color attach="background" args={["#161625"]} />
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 5, 5]} intensity={1.2} />
        <pointLight position={[-5, 3, -5]} intensity={0.8} color="#8b5cf6" />
        <pointLight position={[5, -3, 5]} intensity={0.5} color="#3b82f6" />
        
        <React.Suspense fallback={<FallbackBox />}>
          <NinjaModel isTalking={isTalking} />
        </React.Suspense>
        
        <OrbitControls enableZoom={false} enablePan={false} minPolarAngle={Math.PI/2.5} maxPolarAngle={Math.PI/1.5} />
        <Environment preset="city" />
      </Canvas>

      {/* Personality Selector */}
      <div style={{
        position: "absolute",
        top: 12,
        right: 12,
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}>
        <button
          onClick={() => setShowSelector(!showSelector)}
          style={{
            padding: "6px 12px",
            background: "rgba(10, 10, 15, 0.85)",
            backdropFilter: "blur(8px)",
            border: "1px solid #27272a",
            borderRadius: 12,
            color: "#e4e4e7",
            fontSize: 12,
            cursor: "pointer",
          }}
        >
          🎭 {personality}
        </button>
        
        {showSelector && (
          <div style={{
            padding: 8,
            background: "rgba(10, 10, 15, 0.95)",
            backdropFilter: "blur(8px)",
            border: "1px solid #27272a",
            borderRadius: 12,
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}>
            {personalities.map((p) => (
              <button
                key={p}
                onClick={() => { changePersonality(p); setShowSelector(false); }}
                style={{
                  padding: "4px 8px",
                  background: personality === p ? "rgba(139, 92, 246, 0.3)" : "transparent",
                  border: "none",
                  borderRadius: 6,
                  color: "#e4e4e7",
                  fontSize: 11,
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Status Bar */}
      <div style={{
        position: "absolute",
        bottom: 12,
        left: "50%",
        transform: "translateX(-50%)",
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 16px",
        background: "rgba(10, 10, 15, 0.85)",
        backdropFilter: "blur(8px)",
        borderRadius: 24,
        fontSize: 13,
        color: "#a1a1aa",
        border: "1px solid #27272a",
      }}>
        <div style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: isListening || isTalking ? "#f97316" : "#8b5cf6",
          animation: (isListening || isTalking) ? "pulse 0.5s ease-in-out infinite" : "none",
        }} />
        <span>{status === "Listo" ? "SISTEMA ACTIVO" : status}</span>
      </div>

      {/* PTT Hint */}
      <div style={{
        position: "absolute",
        top: 12,
        left: "50%",
        transform: "translateX(-50%)",
        padding: "6px 12px",
        background: "rgba(10, 10, 15, 0.85)",
        backdropFilter: "blur(8px)",
        borderRadius: 16,
        fontSize: 12,
        color: "#a1a1aa",
        border: "1px solid #27272a",
      }}>
        Mantén ESPACIO para hablar
      </div>
    </div>
  );
}

const rootElement = document.getElementById("avatar-container");
if (rootElement) {
  ReactDOM.createRoot(rootElement).render(<AvatarViewer />);
}
