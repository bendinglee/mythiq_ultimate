import * as Phaser from "phaser";

export default class MainScene extends Phaser.Scene {
  constructor() { super("main"); }

  preload() {
    this.load.image("playerShip", "/playerShip.png");
    this.load.image("coinTex", "/coin.png");
    this.load.image("enemyTex", "/enemy.png");
  }

  create() {
    this.cameras.main.setBackgroundColor("#0b0f1a");
    this.physics.world.setBounds(0, 0, 3840, 2160);

    this.player = this.physics.add.image(1920, 1080, "playerShip");
    this.player.setCollideWorldBounds(true);
    this.player.setDamping(true);
    this.player.setDrag(0.92);
    this.player.setMaxVelocity(900);

    this.cursors = this.input.keyboard.createCursorKeys();
    this.keys = this.input.keyboard.addKeys("W,A,S,D,SPACE");

    this.bullets = this.physics.add.group({ classType: Phaser.Physics.Arcade.Image, maxSize: 60 });
    this.nextShotAt = 0;

    this.enemies = this.physics.add.group({ classType: Phaser.Physics.Arcade.Image });
    this.coins = this.physics.add.group({ classType: Phaser.Physics.Arcade.Image });

    this.score = 0;
    this.combo = 0;

    this.scoreText = this.add.text(60, 50, "SCORE 0", { fontSize: "64px", color: "#ffffff" }).setScrollFactor(0);
    this.comboText = this.add.text(60, 130, "COMBO x0", { fontSize: "48px", color: "#9be7ff" }).setScrollFactor(0);

    this.cameras.main.startFollow(this.player, true, 0.08, 0.08);
    this.cameras.main.setZoom(1);

    this.physics.add.overlap(this.bullets, this.enemies, (b,e)=>this.hitEnemy(b,e));
    this.physics.add.overlap(this.player, this.coins, (_p,c)=>this.pickCoin(c));
    this.physics.add.overlap(this.player, this.enemies, ()=>this.playerHit());

    this.wave = 0;
    this.time.addEvent({ delay: 1600, loop: true, callback: ()=>this.spawnWave() });
  }

  shoot() {
    const now = this.time.now;
    if (now < this.nextShotAt) return;
    this.nextShotAt = now + 140;

    const b = this.bullets.get(this.player.x, this.player.y, "coinTex");
    if (!b) return;

    b.setActive(true).setVisible(true);
    b.body.reset(this.player.x, this.player.y);
    b.setScale(0.55);
    b.setDepth(5);

    const ptr = this.input.activePointer;
    const wp = this.cameras.main.getWorldPoint(ptr.x, ptr.y);
    const ang = Phaser.Math.Angle.Between(this.player.x, this.player.y, wp.x, wp.y);
    b.body.setVelocity(Math.cos(ang)*1400, Math.sin(ang)*1400);

    this.time.delayedCall(900, ()=>{ if (b.active) this.bullets.killAndHide(b); });
  }

  spawnWave() {
    this.wave += 1;
    const n = Math.min(3 + Math.floor(this.wave/2), 12);
    for (let i=0;i<n;i++) {
      const side = Phaser.Math.Between(0,3);
      let x=0,y=0;
      if (side===0){ x=Phaser.Math.Between(0,3840); y=-50; }
      if (side===1){ x=3890; y=Phaser.Math.Between(0,2160); }
      if (side===2){ x=Phaser.Math.Between(0,3840); y=2210; }
      if (side===3){ x=-50; y=Phaser.Math.Between(0,2160); }

      const e = this.enemies.get(x,y,"enemyTex");
      if (!e) continue;

      e.setActive(true).setVisible(true);
      e.body.reset(x,y);
      e.setScale(0.9);
      e.setDepth(2);

      const spd = 180 + this.wave*6;
      this.physics.moveToObject(e, this.player, spd);
    }
  }

  hitEnemy(b,e) {
    this.bullets.killAndHide(b);
    e.disableBody(true, true);

    this.cameras.main.shake(60, 0.006);

    this.combo = Math.min(this.combo + 1, 50);
    this.score += 10 * (1 + Math.floor(this.combo/5));
    this.scoreText.setText("SCORE " + this.score);
    this.comboText.setText("COMBO x" + this.combo);

    const c = this.coins.get(e.x, e.y, "coinTex");
    if (c) {
      c.setActive(true).setVisible(true);
      c.body.reset(e.x, e.y);
      c.setScale(0.8);
      c.setDepth(3);
      c.body.setVelocity(Phaser.Math.Between(-80,80), Phaser.Math.Between(-80,80));
    }
  }

  pickCoin(c) {
    c.disableBody(true,true);
    this.score += 5;
    this.scoreText.setText("SCORE " + this.score);
  }

  playerHit() {
    this.combo = 0;
    this.comboText.setText("COMBO x0");
    this.cameras.main.flash(90, 255, 80, 80);
  }

  update() {
    const up = this.cursors.up.isDown || this.keys.W.isDown;
    const down = this.cursors.down.isDown || this.keys.S.isDown;
    const left = this.cursors.left.isDown || this.keys.A.isDown;
    const right = this.cursors.right.isDown || this.keys.D.isDown;

    const ax = (left?-1:0) + (right?1:0);
    const ay = (up?-1:0) + (down?1:0);

    const accel = 1600;
    this.player.setAcceleration(ax*accel, ay*accel);

    if (this.keys.SPACE.isDown) this.shoot();
  }
}
