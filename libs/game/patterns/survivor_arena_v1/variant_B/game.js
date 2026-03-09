import * as Phaser from "phaser";
import MainScene from "./MainScene.js";

const config = {
  type: Phaser.AUTO,
  parent: "game-container",
  backgroundColor: "#05060a",
  physics: {
    default: "arcade",
    arcade: { gravity: { y: 0 }, debug: false }
  },
  scale: {
    parent: "game-container",
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: 3840,
    height: 2160
  },
  scene: [MainScene]
};

export default config;
