import { useEffect, useState } from "react";
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";
import * as THREE from "three";

const cache = new Map<string, Promise<THREE.Texture>>();

/** Loads a texture from public/ and blocks rendering until it is ready. */
export const useTexture = (file: string, color = true) => {
  const [tex, setTex] = useState<THREE.Texture | null>(null);
  const [handle] = useState(() => delayRender(`Loading texture ${file}`));

  useEffect(() => {
    let p = cache.get(file);
    if (!p) {
      p = new Promise<THREE.Texture>((resolve, reject) => {
        new THREE.TextureLoader().load(staticFile(file), resolve, undefined, reject);
      });
      cache.set(file, p);
    }
    p.then((t) => {
      t.colorSpace = color ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      t.anisotropy = 8;
      t.needsUpdate = true;
      setTex(t);
    }).catch((e) => cancelRender(e));
  }, [file, color]);

  useEffect(() => {
    if (tex) continueRender(handle);
  }, [tex, handle]);

  return tex;
};
