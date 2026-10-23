import React, { useMemo } from "react";
import * as THREE from "three";

/**
 * A generic long-haul twin (777-like proportions), built procedurally so no
 * third-party model or livery is needed. Nose points to +X, right wing to +Z.
 * 1 unit ≈ 10 m.
 */
export const Airliner: React.FC<{ readonly frame: number }> = ({ frame }) => {
  const fuselage = useMemo(() => {
    const prof: [number, number][] = [
      [0.0, -3.25],
      [0.07, -3.18],
      [0.17, -2.95],
      [0.27, -2.45],
      [0.31, -1.8],
      [0.31, 2.35],
      [0.28, 2.75],
      [0.2, 3.02],
      [0.1, 3.17],
      [0.0, 3.23],
    ];
    const g = new THREE.LatheGeometry(
      prof.map(([r, y]) => new THREE.Vector2(r, y)),
      56,
    );
    g.rotateZ(-Math.PI / 2);
    return g;
  }, []);

  const wing = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(0.95, 0);
    s.lineTo(-0.9, 3.05);
    s.lineTo(-1.22, 3.05);
    s.lineTo(-0.75, 0.9);
    s.lineTo(-0.7, 0);
    s.closePath();
    const g = new THREE.ExtrudeGeometry(s, { depth: 0.07, bevelEnabled: true, bevelThickness: 0.02, bevelSize: 0.02, bevelSegments: 2 });
    g.rotateX(-Math.PI / 2);
    return g;
  }, []);

  const hstab = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-2.4, 0);
    s.lineTo(-3.05, 1.15);
    s.lineTo(-3.3, 1.15);
    s.lineTo(-3.12, 0);
    s.closePath();
    const g = new THREE.ExtrudeGeometry(s, { depth: 0.04, bevelEnabled: false });
    g.rotateX(-Math.PI / 2);
    return g;
  }, []);

  const fin = useMemo(() => {
    const s = new THREE.Shape();
    s.moveTo(-1.95, 0.2);
    s.lineTo(-2.85, 1.6);
    s.lineTo(-3.2, 1.6);
    s.lineTo(-3.15, 0.15);
    s.closePath();
    const g = new THREE.ExtrudeGeometry(s, { depth: 0.05, bevelEnabled: true, bevelThickness: 0.01, bevelSize: 0.01, bevelSegments: 1 });
    g.translate(0, 0, -0.025);
    return g;
  }, []);

  const windows = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let x = -2.2; x <= 2.45; x += 0.085) {
      if (x > -0.25 && x < 0.15) continue; // over-wing gap
      pts.push(new THREE.Vector3(x, 0.08, 0.303), new THREE.Vector3(x, 0.08, -0.303));
    }
    return pts;
  }, []);

  const skin = useMemo(
    () => new THREE.MeshStandardMaterial({ color: "#d9dee5", metalness: 0.35, roughness: 0.42, side: THREE.DoubleSide }),
    [],
  );
  const dark = useMemo(() => new THREE.MeshStandardMaterial({ color: "#2a3038", metalness: 0.5, roughness: 0.5 }), []);
  const strobe = frame % 36 < 2;
  const beacon = frame % 30 < 4;

  const Engine: React.FC<{ readonly z: number }> = ({ z }) => (
    <group position={[0.5, -0.36, z]}>
      <mesh rotation={[0, 0, Math.PI / 2]} material={skin}>
        <cylinderGeometry args={[0.17, 0.15, 0.78, 32, 1, true]} />
      </mesh>
      <mesh position={[0.39, 0, 0]} rotation={[0, 0, Math.PI / 2]} material={dark}>
        <circleGeometry args={[0.165, 32]} />
      </mesh>
      <mesh position={[0, 0.17, 0]} material={skin}>
        <boxGeometry args={[0.5, 0.18, 0.04]} />
      </mesh>
    </group>
  );

  return (
    <group>
      <mesh geometry={fuselage} material={skin} />
      <group position={[-0.05, -0.16, 0]} rotation={[0.1, 0, 0]}>
        <mesh geometry={wing} material={skin} />
        <mesh position={[-0.98, 0.06, -3.06]}>
          <sphereGeometry args={[0.035, 12, 12]} />
          <meshBasicMaterial color="#ff2a2a" toneMapped={false} />
        </mesh>
        {strobe ? (
          <pointLight position={[-1.1, 0.1, -3.1]} color="#ffffff" intensity={6} distance={3} />
        ) : null}
      </group>
      <group position={[-0.05, -0.16, 0]} rotation={[-0.1, 0, 0]} scale={[1, 1, -1]}>
        <mesh geometry={wing} material={skin} />
        <mesh position={[-0.98, 0.06, -3.06]}>
          <sphereGeometry args={[0.035, 12, 12]} />
          <meshBasicMaterial color="#2aff7a" toneMapped={false} />
        </mesh>
      </group>
      <Engine z={-1.05} />
      <Engine z={1.05} />
      <group position={[0, 0.12, 0]}>
        <mesh geometry={hstab} material={skin} />
        <group scale={[1, 1, -1]}>
          <mesh geometry={hstab} material={skin} />
        </group>
      </group>
      <mesh geometry={fin} material={skin} />
      {windows.map((p, i) => (
        <mesh key={i} position={p}>
          <boxGeometry args={[0.035, 0.05, 0.01]} />
          <meshBasicMaterial color="#ffd9a0" toneMapped={false} />
        </mesh>
      ))}
      <mesh position={[0.2, 0.32, 0]}>
        <sphereGeometry args={[0.03, 10, 10]} />
        <meshBasicMaterial color={beacon ? "#ff3030" : "#401010"} toneMapped={false} />
      </mesh>
      {strobe ? (
        <mesh position={[-0.98, -0.1, 3.06]}>
          <sphereGeometry args={[0.07, 10, 10]} />
          <meshBasicMaterial color="#ffffff" toneMapped={false} />
        </mesh>
      ) : null}
    </group>
  );
};
