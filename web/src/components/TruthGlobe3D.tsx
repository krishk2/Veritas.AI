"use client";

import React, { useEffect, useRef } from "react";
import * as THREE from "three";

interface TruthGlobe3DProps {
  verdict?: "TRUE" | "FALSE" | "MISLEADING" | "UNVERIFIED" | null;
  activeNodeCount?: number;
}

export const TruthGlobe3D: React.FC<TruthGlobe3DProps> = ({
  verdict,
  activeNodeCount = 24,
}) => {
  const mountRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const currentMount = mountRef.current;
    if (!currentMount) return;

    const width = currentMount.clientWidth || 400;
    const height = currentMount.clientHeight || 350;

    // Scene, Camera, Renderer
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.z = 240;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    currentMount.appendChild(renderer.domElement);

    // Particle Sphere representing Global Truth Network
    const particleCount = 450;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    // Dynamic accent color based on verdict
    const baseColor =
      verdict === "TRUE"
        ? new THREE.Color(0x10b981) // emerald
        : verdict === "FALSE"
        ? new THREE.Color(0xf43f5e) // rose
        : verdict === "MISLEADING"
        ? new THREE.Color(0xf59e0b) // amber
        : new THREE.Color(0x06b6d4); // cyan

    const radius = 80;
    for (let i = 0; i < particleCount; i++) {
      const phi = Math.acos(-1 + (2 * i) / particleCount);
      const theta = Math.sqrt(particleCount * Math.PI) * phi;

      positions[i * 3] = radius * Math.cos(theta) * Math.sin(phi);
      positions[i * 3 + 1] = radius * Math.sin(theta) * Math.sin(phi);
      positions[i * 3 + 2] = radius * Math.cos(phi);

      colors[i * 3] = baseColor.r * (0.6 + Math.random() * 0.4);
      colors[i * 3 + 1] = baseColor.g * (0.6 + Math.random() * 0.4);
      colors[i * 3 + 2] = baseColor.b * (0.6 + Math.random() * 0.4);
    }

    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
      size: 2.2,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
    });

    const sphere = new THREE.Points(geometry, material);
    scene.add(sphere);

    // Wireframe Outer Shield
    const shieldGeometry = new THREE.IcosahedronGeometry(95, 2);
    const shieldMaterial = new THREE.MeshBasicMaterial({
      color: baseColor,
      wireframe: true,
      transparent: true,
      opacity: 0.12,
    });
    const shield = new THREE.Mesh(shieldGeometry, shieldMaterial);
    scene.add(shield);

    // Interactive mouse parallax
    let mouseX = 0;
    let mouseY = 0;
    const handleMouseMove = (e: MouseEvent) => {
      const rect = currentMount.getBoundingClientRect();
      mouseX = ((e.clientX - rect.left) / width - 0.5) * 2;
      mouseY = -((e.clientY - rect.top) / height - 0.5) * 2;
    };
    currentMount.addEventListener("mousemove", handleMouseMove);

    // Animation Loop
    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);

      sphere.rotation.y += 0.003;
      sphere.rotation.x += 0.001;
      shield.rotation.y -= 0.0015;

      // Smooth camera tilt towards mouse
      camera.position.x += (mouseX * 30 - camera.position.x) * 0.05;
      camera.position.y += (mouseY * 30 - camera.position.y) * 0.05;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    };

    animate();

    // Resize handling
    const handleResize = () => {
      if (!currentMount) return;
      const newW = currentMount.clientWidth;
      const newH = currentMount.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      currentMount.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("resize", handleResize);
      if (currentMount.contains(renderer.domElement)) {
        currentMount.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
      shieldGeometry.dispose();
      shieldMaterial.dispose();
      renderer.dispose();
    };
  }, [verdict, activeNodeCount]);

  return (
    <div className="relative w-full h-[320px] rounded-2xl bg-[#090F1E]/80 border border-white/5 overflow-hidden flex items-center justify-center">
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />
      <div className="absolute top-4 left-4 pointer-events-none">
        <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-slate-300">
          Neo4j Provenance Graph
        </span>
      </div>
      <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between text-xs text-slate-400 pointer-events-none">
        <span>Verified Nodes: {activeNodeCount}</span>
        <span className="font-mono text-[11px] text-cyan-400">Trace-the-Source Live</span>
      </div>
    </div>
  );
};
