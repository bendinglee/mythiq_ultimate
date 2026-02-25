(() => {
  const W = 800, H = 600;

  let score = 0;
  const setScore = (v) => { score = v; document.getElementById("score").textContent = "score: " + score; };

  class MainScene extends Phaser.Scene {
    constructor(){ super("main"); }
    preload(){}

    create(){
      this.cameras.main.setBackgroundColor("#0b0f14");

      this.player = this.add.rectangle(W/2, H-80, 40, 40, 0x4cc9f0);
      this.physics.add.existing(this.player);
      this.player.body.setCollideWorldBounds(true);

      this.cursors = this.input.keyboard.createCursorKeys();

      this.orbs = this.physics.add.group();
      this.haz = this.physics.add.group();

      this.spawnTimer = 0;
      this.hazTimer = 0;

      setScore(0);

      this.physics.add.overlap(this.player, this.orbs, (p, o) => {
        o.destroy();
        setScore(score + 10);
      });

      this.physics.add.overlap(this.player, this.haz, () => {
        this.scene.restart();
      });
    }

    update(t, dt){
      const speed = 420;
      const body = this.player.body;
      body.setVelocity(0);

      if (this.cursors.left.isDown) body.setVelocityX(-speed);
      if (this.cursors.right.isDown) body.setVelocityX(speed);
      if (this.cursors.up.isDown) body.setVelocityY(-speed);
      if (this.cursors.down.isDown) body.setVelocityY(speed);

      this.spawnTimer += dt;
      this.hazTimer += dt;

      if (this.spawnTimer > 700){
        this.spawnTimer = 0;
        const x = Phaser.Math.Between(30, W-30);
        const orb = this.add.circle(x, -10, 10, 0x80ff72);
        this.physics.add.existing(orb);
        orb.body.setVelocityY(220);
        orb.body.setCircle(10);
        this.orbs.add(orb);
      }

      if (this.hazTimer > 900){
        this.hazTimer = 0;
        const x = Phaser.Math.Between(30, W-30);
        const r = Phaser.Math.Between(14, 24);
        const hz = this.add.circle(x, -20, r, 0xff4d6d);
        this.physics.add.existing(hz);
        hz.body.setVelocityY(320);
        hz.body.setCircle(r);
        this.haz.add(hz);
      }

      // cleanup
      for (const g of [this.orbs, this.haz]){
        g.getChildren().forEach(o => {
          if (o.y > H + 80) o.destroy();
        });
      }
    }
  }

  const config = {
    type: Phaser.AUTO,
    parent: "game",
    width: W,
    height: H,
    physics: { default: "arcade", arcade: { debug: false } },
    scene: [MainScene],
    scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH }
  };

  new Phaser.Game(config);
})();
