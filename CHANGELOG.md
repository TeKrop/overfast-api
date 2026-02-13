# CHANGELOG

<!-- version list -->

## v3.38.2 (2026-02-13)

### Bug Fixes

- **parsers**: Correct competitive gamemode mapping
  ([#360](https://github.com/TeKrop/overfast-api/pull/360),
  [`4049ce1`](https://github.com/TeKrop/overfast-api/commit/4049ce17bf2eddb1997d358689d581d6726f2e55))


## v3.38.1 (2026-02-13)

### Bug Fixes

- Fixed dashboard issues and missing category key on player profile endpoint
  ([#358](https://github.com/TeKrop/overfast-api/pull/358),
  [`6c72dab`](https://github.com/TeKrop/overfast-api/commit/6c72dabfd753f2af9a9973f5c5f8474faaaac591))


## v3.38.0 (2026-02-12)

### Features

- Phase 2 - Complete monitoring infrastructure with enhanced dashboards
  ([#357](https://github.com/TeKrop/overfast-api/pull/357),
  [`ea563a2`](https://github.com/TeKrop/overfast-api/commit/ea563a2497a398974be0a97e4020cddbc2f56a81))


## v3.37.0 (2026-02-11)

### Features

- Update heroes hitpoints ([#356](https://github.com/TeKrop/overfast-api/pull/356),
  [`97bbdb7`](https://github.com/TeKrop/overfast-api/commit/97bbdb7055254039c9b54e38a5e5382a2bc7e15e))


## v3.36.0 (2026-02-11)

### Features

- Add support for heroes data related to Stadium
  ([#355](https://github.com/TeKrop/overfast-api/pull/355),
  [`54591e0`](https://github.com/TeKrop/overfast-api/commit/54591e06c6c9137815258e89abd21fff13b2e4a5))


## v3.35.2 (2026-02-10)

### Bug Fixes

- Put back proper error management on some controllers after rework
  ([#353](https://github.com/TeKrop/overfast-api/pull/353),
  [`e916d98`](https://github.com/TeKrop/overfast-api/commit/e916d986828cdbac4f5b795a554383cad69e0514))


## v3.35.1 (2026-02-10)

### Bug Fixes

- Fixed issue with missing category names on profile pages sometimes
  ([#352](https://github.com/TeKrop/overfast-api/pull/352),
  [`a4ae304`](https://github.com/TeKrop/overfast-api/commit/a4ae304bc2b7c30114de8830b8cdd88cf4a6b11e))


## v3.35.0 (2026-02-10)

### Features

- Improved discord webhook message format ([#351](https://github.com/TeKrop/overfast-api/pull/351),
  [`5b319aa`](https://github.com/TeKrop/overfast-api/commit/5b319aa20e24facd2d0a696ccc0cd95011ba0578))


## v3.34.4 (2026-02-10)

### Bug Fixes

- Several bugfixes on player profiles edge cases
  ([#350](https://github.com/TeKrop/overfast-api/pull/350),
  [`0192bdf`](https://github.com/TeKrop/overfast-api/commit/0192bdf540c16aacb37040bbe86547c86c48bbb6))


## v3.34.3 (2026-02-09)

### Bug Fixes

- Fixed issue when players didn't have stats
  ([#349](https://github.com/TeKrop/overfast-api/pull/349),
  [`4e7cf15`](https://github.com/TeKrop/overfast-api/commit/4e7cf15ebb986ed47f206648c7b08ca4583e6e5c))


## v3.34.2 (2026-02-08)

### Bug Fixes

- Forcing en-us versions of player profile pages to be loaded for the API
  ([#348](https://github.com/TeKrop/overfast-api/pull/348),
  [`1f5bceb`](https://github.com/TeKrop/overfast-api/commit/1f5bceb5ce42fd9ca253d457f73de5fcac781796))


## v3.34.1 (2026-02-08)

### Bug Fixes

- Fixed unknown player issue ([#347](https://github.com/TeKrop/overfast-api/pull/347),
  [`dc4a536`](https://github.com/TeKrop/overfast-api/commit/dc4a536d956943519bda4487e653771685efdebb))


## v3.34.0 (2026-02-08)

### Features

- Started to rework project with DDD (ports and adapters)
  ([#346](https://github.com/TeKrop/overfast-api/pull/346),
  [`17cb27e`](https://github.com/TeKrop/overfast-api/commit/17cb27e8ef43a885ccf9f558cf5411a5a66856d8))


## v3.33.0 (2026-02-05)

### Features

- Added new heroes and removed the 2 from game name
  ([#345](https://github.com/TeKrop/overfast-api/pull/345),
  [`2965796`](https://github.com/TeKrop/overfast-api/commit/2965796a36771dc25738c4a0471c1431236084d4))


## v3.32.1 (2026-02-01)

### Bug Fixes

- Revert "feat: added monitoring regarding Blizzard rate limits (#343)"
  ([#344](https://github.com/TeKrop/overfast-api/pull/344),
  [`2e9a3b6`](https://github.com/TeKrop/overfast-api/commit/2e9a3b6e05ec2d9f2771714149ae7e4b05f0c64b))


## v3.32.0 (2026-02-01)

### Features

- Added monitoring regarding Blizzard rate limits
  ([#343](https://github.com/TeKrop/overfast-api/pull/343),
  [`05b5203`](https://github.com/TeKrop/overfast-api/commit/05b52033f0e874a873d5c2c11087a16ecb365c72))


## v3.31.0 (2026-02-01)

### Features

- Added ty type checker ([#342](https://github.com/TeKrop/overfast-api/pull/342),
  [`dc5548a`](https://github.com/TeKrop/overfast-api/commit/dc5548afed2c2d3ec78b3752ff20486ef059dfba))


## v3.30.0 (2026-01-04)

### Features

- **monitoring**: Added Sentry support for monitoring
  ([#341](https://github.com/TeKrop/overfast-api/pull/341),
  [`0bf2f26`](https://github.com/TeKrop/overfast-api/commit/0bf2f261d7e41c177a6ab10ad9f23562c10b4baf))


## v3.29.1 (2025-12-24)

### Bug Fixes

- Added unknown players negative caching to improve performances
  ([#340](https://github.com/TeKrop/overfast-api/pull/340),
  [`fe66b14`](https://github.com/TeKrop/overfast-api/commit/fe66b142680b8b30bf913eb5afdc2099e39597a9))


## v3.29.0 (2025-12-24)

### Features

- **maps**: Added Wuxing University ([#339](https://github.com/TeKrop/overfast-api/pull/339),
  [`52d90fa`](https://github.com/TeKrop/overfast-api/commit/52d90fa561edc91b9746e91734044cdbb5ef5ba6))


## v3.28.1 (2025-12-16)

### Bug Fixes

- Fixed players search endpoint after Blizzard removal of Battle Tag on search
  ([#338](https://github.com/TeKrop/overfast-api/pull/338),
  [`d13e64c`](https://github.com/TeKrop/overfast-api/commit/d13e64cf17f8b446d6e0a497b5290732cdb6ea29))


## v3.28.0 (2025-12-11)

### Build System

- **deps**: Bump pydantic from 2.12.4 to 2.12.5
  ([#331](https://github.com/TeKrop/overfast-api/pull/331),
  [`ec65741`](https://github.com/TeKrop/overfast-api/commit/ec65741068bc3ab02e29c528a0c38ac96eb34901))

- **deps**: Bump ruff from 0.14.6 to 0.14.7
  ([#332](https://github.com/TeKrop/overfast-api/pull/332),
  [`3f929b0`](https://github.com/TeKrop/overfast-api/commit/3f929b01c1aa307d68e33dbc2772b833d4b3369e))

- **deps**: Bump selectolax from 0.4.3 to 0.4.4
  ([#334](https://github.com/TeKrop/overfast-api/pull/334),
  [`792b382`](https://github.com/TeKrop/overfast-api/commit/792b3821af95d73746cb2afe40d8a4dd416c2546))

- **deps**: Update fastapi[standard-no-fastapi-cloud-cli] requirement
  ([#333](https://github.com/TeKrop/overfast-api/pull/333),
  [`8e7d59c`](https://github.com/TeKrop/overfast-api/commit/8e7d59cc242c0a7e505336ca07b2392a694c7b4b))

### Features

- Update Vendetta hitpoints ([#335](https://github.com/TeKrop/overfast-api/pull/335),
  [`a4c596d`](https://github.com/TeKrop/overfast-api/commit/a4c596dcdea15ff535d1e9b8b6021f366e4d28a1))


## v3.27.0 (2025-11-28)

### Features

- Update heroes hitpoints ([#330](https://github.com/TeKrop/overfast-api/pull/330),
  [`07e18cb`](https://github.com/TeKrop/overfast-api/commit/07e18cb2de8f950d29bef491a128e1e1671cc329))


## v3.26.1 (2025-11-26)

### Bug Fixes

- Update game mode screenshots ([#329](https://github.com/TeKrop/overfast-api/pull/329),
  [`6d02203`](https://github.com/TeKrop/overfast-api/commit/6d022036ef4fbefface8c8319a95d4d6332c21fe))


## v3.26.0 (2025-11-25)

### Build System

- **deps**: Bump pre-commit from 4.4.0 to 4.5.0
  ([#326](https://github.com/TeKrop/overfast-api/pull/326),
  [`3f75440`](https://github.com/TeKrop/overfast-api/commit/3f7544021c71418321c0411d12fd84e1335c7c32))

- **deps**: Bump pytest from 8.4.2 to 9.0.1
  ([#325](https://github.com/TeKrop/overfast-api/pull/325),
  [`09da432`](https://github.com/TeKrop/overfast-api/commit/09da432826ca061e6061fa3923c1d48a8913b69f))

- **deps**: Bump ruff from 0.14.5 to 0.14.6
  ([#324](https://github.com/TeKrop/overfast-api/pull/324),
  [`8d9abbb`](https://github.com/TeKrop/overfast-api/commit/8d9abbb77a1941384c09fce9c3d8874522c4420c))

### Chores

- Added AGENTS.md
  ([`669e9f1`](https://github.com/TeKrop/overfast-api/commit/669e9f16e9139ebece69b83c5a1da7e300cd15f3))

### Features

- **redoc**: Added style to Redoc documentation
  ([#327](https://github.com/TeKrop/overfast-api/pull/327),
  [`08e480a`](https://github.com/TeKrop/overfast-api/commit/08e480a8655da245cf80e4c9c2d29914bdf40445))


## v3.25.0 (2025-11-17)

### Build System

- **deps**: Bump pre-commit from 4.3.0 to 4.4.0
  ([#318](https://github.com/TeKrop/overfast-api/pull/318),
  [`7dd43e7`](https://github.com/TeKrop/overfast-api/commit/7dd43e79420f078f70b8cdd42cace0ad1472a30f))

- **deps**: Bump pydantic from 2.12.3 to 2.12.4
  ([#316](https://github.com/TeKrop/overfast-api/pull/316),
  [`0c5d426`](https://github.com/TeKrop/overfast-api/commit/0c5d4260b564d2b38bed009fcdd68846f2ba61f7))

- **deps**: Bump pydantic-settings from 2.11.0 to 2.12.0
  ([#321](https://github.com/TeKrop/overfast-api/pull/321),
  [`f788439`](https://github.com/TeKrop/overfast-api/commit/f788439907cd5dbb6856e28fbc1810788025ac6b))

- **deps**: Bump pytest-asyncio from 1.2.0 to 1.3.0
  ([#322](https://github.com/TeKrop/overfast-api/pull/322),
  [`fed39dd`](https://github.com/TeKrop/overfast-api/commit/fed39ddbb7df10638f2c1087a1b9fc2e9d77208b))

- **deps**: Bump ruff from 0.14.3 to 0.14.4
  ([#317](https://github.com/TeKrop/overfast-api/pull/317),
  [`193d229`](https://github.com/TeKrop/overfast-api/commit/193d229bc3f0aa7a1c37449d2bb1ce8b3c07a727))

- **deps**: Bump ruff from 0.14.4 to 0.14.5
  ([#320](https://github.com/TeKrop/overfast-api/pull/320),
  [`85dc7fb`](https://github.com/TeKrop/overfast-api/commit/85dc7fb6c448151100697c356357a4e6a1646edd))

- **deps**: Bump selectolax from 0.4.0 to 0.4.3
  ([#319](https://github.com/TeKrop/overfast-api/pull/319),
  [`774cb9b`](https://github.com/TeKrop/overfast-api/commit/774cb9b68d989d53d0f1e83739284eef405fb210))

### Features

- Added support for Vendetta hero ([#323](https://github.com/TeKrop/overfast-api/pull/323),
  [`8f467e2`](https://github.com/TeKrop/overfast-api/commit/8f467e256ff04e5bb8d6ddfc7fcfd3032428c2f7))


## v3.24.1 (2025-11-08)

### Bug Fixes

- Fixed ponctual issue with KeyError ([#315](https://github.com/TeKrop/overfast-api/pull/315),
  [`4523e14`](https://github.com/TeKrop/overfast-api/commit/4523e144f5a68d6ed55c5f35ac98495edbf6ea69))

### Build System

- **deps**: Bump memray from 1.18.0 to 1.19.1
  ([#312](https://github.com/TeKrop/overfast-api/pull/312),
  [`48399f8`](https://github.com/TeKrop/overfast-api/commit/48399f87684fdbdeefd2238fddfb6caab5cd8b72))

- **deps**: Bump pydantic from 2.12.0 to 2.12.3
  ([#310](https://github.com/TeKrop/overfast-api/pull/310),
  [`3d72d64`](https://github.com/TeKrop/overfast-api/commit/3d72d64d39581c05e1ec22e9e3dcfc5b1ef52656))

- **deps**: Bump ruff from 0.14.0 to 0.14.2
  ([#311](https://github.com/TeKrop/overfast-api/pull/311),
  [`9dc5f96`](https://github.com/TeKrop/overfast-api/commit/9dc5f9608ace71a3cc16a0bb361d77a12fe846b0))

- **deps**: Bump ruff from 0.14.2 to 0.14.3
  ([#313](https://github.com/TeKrop/overfast-api/pull/313),
  [`9b9b6dc`](https://github.com/TeKrop/overfast-api/commit/9b9b6dc4b940d70dae34e707f32f41c937e5790b))

- **deps**: Update fastapi[standard-no-fastapi-cloud-cli] requirement
  ([#309](https://github.com/TeKrop/overfast-api/pull/309),
  [`6628026`](https://github.com/TeKrop/overfast-api/commit/6628026343f42a62d89f1ebf4c764b201697127b))


## v3.24.0 (2025-10-15)

### Build System

- **deps**: Bump pydantic from 2.11.10 to 2.12.0
  ([#307](https://github.com/TeKrop/overfast-api/pull/307),
  [`77716eb`](https://github.com/TeKrop/overfast-api/commit/77716eb470fd954eb0f124ed47df3331f779e65e))

- **deps**: Bump pydantic from 2.11.9 to 2.11.10
  ([#305](https://github.com/TeKrop/overfast-api/pull/305),
  [`701b6df`](https://github.com/TeKrop/overfast-api/commit/701b6dfeb31b3a08239324066835eda31450abf0))

- **deps**: Update fastapi[standard-no-fastapi-cloud-cli] requirement
  ([#306](https://github.com/TeKrop/overfast-api/pull/306),
  [`1916eed`](https://github.com/TeKrop/overfast-api/commit/1916eed24a9f5abb48e8a56225b060f8d1f43019))

### Features

- Updated python to 3.14 and updated dependencies
  ([#308](https://github.com/TeKrop/overfast-api/pull/308),
  [`f6861fb`](https://github.com/TeKrop/overfast-api/commit/f6861fb926a89026728221b811cfc3f3c0b149d7))


## v3.23.1 (2025-10-05)

### Bug Fixes

- Added support for old player summary format still being used in some regions
  ([#304](https://github.com/TeKrop/overfast-api/pull/304),
  [`c5c7c73`](https://github.com/TeKrop/overfast-api/commit/c5c7c739c440c208a8c92c648d36fe46cd35d721))


## v3.23.0 (2025-09-29)

### Build System

- **deps**: Bump pydantic-settings from 2.10.1 to 2.11.0
  ([#300](https://github.com/TeKrop/overfast-api/pull/300),
  [`ef99174`](https://github.com/TeKrop/overfast-api/commit/ef991749da7d304aa38ef42909a7d74b52cccce1))

- **deps**: Bump selectolax from 0.3.34 to 0.4.0
  ([#301](https://github.com/TeKrop/overfast-api/pull/301),
  [`0da8f45`](https://github.com/TeKrop/overfast-api/commit/0da8f45f831e4c6b3ac0aa3c5a51844df138a50b))

- **deps**: Update fastapi[standard-no-fastapi-cloud-cli] requirement
  ([#302](https://github.com/TeKrop/overfast-api/pull/302),
  [`a58750b`](https://github.com/TeKrop/overfast-api/commit/a58750bb63aee6af9278dc1bfcd9601d6c323a77))

- **deps**: Update fastapi[standard-no-fastapi-cloud-cli] requirement
  ([#298](https://github.com/TeKrop/overfast-api/pull/298),
  [`f452fb0`](https://github.com/TeKrop/overfast-api/commit/f452fb05d090f422b8e6d0f64ebd8bdd59d7a9e9))

### Features

- Added justfile as makefile alternative ([#303](https://github.com/TeKrop/overfast-api/pull/303),
  [`22fde57`](https://github.com/TeKrop/overfast-api/commit/22fde5792d636607995ddecbb1b8ffb1efbc3ec3))


## v3.22.1 (2025-09-21)

### Bug Fixes

- Adjusted automated deployment workflow
  ([`04ee30c`](https://github.com/TeKrop/overfast-api/commit/04ee30cec0c7c805d0755d6e0185cd283fac92dc))

### Chores

- **config**: Configure Python Semantic Release
  ([`be8eeb4`](https://github.com/TeKrop/overfast-api/commit/be8eeb4b70828e04115c04d25dc4aef60cc58559))


## v3.22.0 (2025-09-18)

### Bug Fixes

- Fixed profile pages after blizzard unlocks update
  ([#297](https://github.com/TeKrop/overfast-api/pull/297),
  [`52b0a8b`](https://github.com/TeKrop/overfast-api/commit/52b0a8b5e47971ba59014319c74076976daa083e))

- Updated deploy gh workflow
  ([`50eda58`](https://github.com/TeKrop/overfast-api/commit/50eda588014a278a49658059aec8d1c374e200c8))

### Build System

- **deps**: Bump pydantic from 2.11.7 to 2.11.9
  ([#295](https://github.com/TeKrop/overfast-api/pull/295),
  [`bc04da1`](https://github.com/TeKrop/overfast-api/commit/bc04da187b443d12b496ee4566832cab304e7ae5))

- **deps**: Bump selectolax from 0.3.29 to 0.3.34
  ([#294](https://github.com/TeKrop/overfast-api/pull/294),
  [`088e58e`](https://github.com/TeKrop/overfast-api/commit/088e58e4152bfe4698f37d1e24a6d83e8770a734))

### Features

- Added gh workflow for automated deploy
  ([`c5d1e4f`](https://github.com/TeKrop/overfast-api/commit/c5d1e4ff5ef99f0b785fee9ad69eae18088f1d95))


## v3.21.1 (2025-09-02)

### Bug Fixes

- Fixed invalid maps URLs and added tests to ensure no regression
  ([#293](https://github.com/TeKrop/overfast-api/pull/293),
  [`c4ae03e`](https://github.com/TeKrop/overfast-api/commit/c4ae03e4e2e2daf4110eaa615002140081bc337a))


## v3.21.0 (2025-08-31)

### Features

- Added new hero statistics endpoint ([#291](https://github.com/TeKrop/overfast-api/pull/291),
  [`37ec14a`](https://github.com/TeKrop/overfast-api/commit/37ec14ad44fa601c0a3bacd335126340f0a98475))


## v3.20.0 (2025-08-30)

### Features

- Added payload race gamemode with two maps
  ([#290](https://github.com/TeKrop/overfast-api/pull/290),
  [`b5d82eb`](https://github.com/TeKrop/overfast-api/commit/b5d82eb59d3c8846923e5d86899c76ee5e515b31))


## v3.19.0 (2025-08-20)

### Features

- Migrated from Redis to Valkey ([#287](https://github.com/TeKrop/overfast-api/pull/287),
  [`ac2ebe0`](https://github.com/TeKrop/overfast-api/commit/ac2ebe002dd75275b6ec5bb04b23d888f3f37d99))


## v3.18.1 (2025-08-18)

### Bug Fixes

- Prevent discord notif on 429 for unlock data
  ([#286](https://github.com/TeKrop/overfast-api/pull/286),
  [`6354e2a`](https://github.com/TeKrop/overfast-api/commit/6354e2ae3171bc0c10cfcc720a1d0656ad87956d))


## v3.18.0 (2025-08-16)

### Features

- Improved redis and nginx interactions for caching
  ([#285](https://github.com/TeKrop/overfast-api/pull/285),
  [`7bbf2c8`](https://github.com/TeKrop/overfast-api/commit/7bbf2c8bd0891c4fdb9128bbb190b73afd5561ac))


## v3.17.0 (2025-08-16)

### Features

- Unlock data cache is now persistent across restarts
  ([#284](https://github.com/TeKrop/overfast-api/pull/284),
  [`f8c4379`](https://github.com/TeKrop/overfast-api/commit/f8c43794016b5e6d8429a7d3fcd8674458be0268))


## v3.16.1 (2025-08-14)

### Bug Fixes

- Fixed issue with missing data-hero-id in stats concerning wuyang
  ([#283](https://github.com/TeKrop/overfast-api/pull/283),
  [`41763f6`](https://github.com/TeKrop/overfast-api/commit/41763f6a53a95f1ee97bf97f8f9c61c1c4a27e83))


## v3.16.0 (2025-08-14)

### Build System

- **deps**: Bump redis from 6.2.0 to 6.4.0 ([#281](https://github.com/TeKrop/overfast-api/pull/281),
  [`0edc69b`](https://github.com/TeKrop/overfast-api/commit/0edc69bd9d32ed6f9c62ba6b60801bc15a90511b))

### Features

- Added wuyang hero in list ([#282](https://github.com/TeKrop/overfast-api/pull/282),
  [`ad3e17f`](https://github.com/TeKrop/overfast-api/commit/ad3e17f2b1c59b57e835039b423d176544cc42e5))


## v3.15.2 (2025-08-09)

### Bug Fixes

- Added new necessary header for retrieving unlocks data
  ([#279](https://github.com/TeKrop/overfast-api/pull/279),
  [`cdb03cf`](https://github.com/TeKrop/overfast-api/commit/cdb03cfc6d099c6405dce728db7949a5095b52f5))


## v3.15.1 (2025-07-18)


## v3.15.0 (2025-07-18)


## v3.14.0 (2025-07-01)

### Bug Fixes

- Fixed openresty build issue ([#268](https://github.com/TeKrop/overfast-api/pull/268),
  [`669625c`](https://github.com/TeKrop/overfast-api/commit/669625cae4e96804051ca8c90a00da3c77009b4f))

### Build System

- **deps**: Bump pydantic from 2.11.5 to 2.11.7
  ([#261](https://github.com/TeKrop/overfast-api/pull/261),
  [`f8dfce9`](https://github.com/TeKrop/overfast-api/commit/f8dfce9ea0ef84a3b7bfda2c6315318758907b6b))

- **deps**: Bump pydantic-settings from 2.9.1 to 2.10.0
  ([#263](https://github.com/TeKrop/overfast-api/pull/263),
  [`b1dde4e`](https://github.com/TeKrop/overfast-api/commit/b1dde4e23badfd48573a596942e6485bc0dcf53d))

- **deps**: Bump selectolax from 0.3.29 to 0.3.30
  ([#262](https://github.com/TeKrop/overfast-api/pull/262),
  [`fc42272`](https://github.com/TeKrop/overfast-api/commit/fc42272d6dad8d2d5823254729c3ea5994a7422d))

### Features

- Added aatlis map ([#269](https://github.com/TeKrop/overfast-api/pull/269),
  [`682a629`](https://github.com/TeKrop/overfast-api/commit/682a62964566941d586703b40a19ef8ef7df1424))

- Updated dependencies ([#270](https://github.com/TeKrop/overfast-api/pull/270),
  [`90d5e67`](https://github.com/TeKrop/overfast-api/commit/90d5e67831a146816c40d92c0ae3cb065f7c7dac))


## v3.13.1 (2025-06-08)

### Build System

- **deps**: Bump pydantic from 2.11.4 to 2.11.5
  ([#257](https://github.com/TeKrop/overfast-api/pull/257),
  [`a42ab00`](https://github.com/TeKrop/overfast-api/commit/a42ab006f3d2fcb932d13a4e23ef9073e1307d6e))

- **deps**: Bump redis from 6.1.0 to 6.2.0 ([#259](https://github.com/TeKrop/overfast-api/pull/259),
  [`5041af3`](https://github.com/TeKrop/overfast-api/commit/5041af32aa6380c6ed367f542b242af042ecbfcf))


## v3.13.0 (2025-05-22)

### Build System

- **deps**: Bump redis from 5.2.1 to 6.1.0 ([#254](https://github.com/TeKrop/overfast-api/pull/254),
  [`0fa9630`](https://github.com/TeKrop/overfast-api/commit/0fa96308a0a53c01ae46e4258bc03da144cfc9df))

### Features

- Added practice range map and gamemode ([#256](https://github.com/TeKrop/overfast-api/pull/256),
  [`f0c869b`](https://github.com/TeKrop/overfast-api/commit/f0c869b6414b10032e7388f0c83d352a2308558e))


## v3.12.1 (2025-05-15)

### Build System

- **deps**: Bump pydantic from 2.11.3 to 2.11.4
  ([#251](https://github.com/TeKrop/overfast-api/pull/251),
  [`2ae45c3`](https://github.com/TeKrop/overfast-api/commit/2ae45c3b6672168dcbeee5950a7a9b96fdd8a430))

- **deps**: Bump selectolax from 0.3.28 to 0.3.29
  ([#252](https://github.com/TeKrop/overfast-api/pull/252),
  [`d127788`](https://github.com/TeKrop/overfast-api/commit/d127788dab40db874488c0cb13ffb62f1b148e3a))


## v3.12.0 (2025-04-27)

### Features

- Added unknown players cache to limit impact on Blizzard rate limits
  ([#250](https://github.com/TeKrop/overfast-api/pull/250),
  [`c3e54dc`](https://github.com/TeKrop/overfast-api/commit/c3e54dce527c0cd798b9583d8e13cf5b9fed7b92))


## v3.11.3 (2025-04-27)

### Features

- Put back search with battletag ([#249](https://github.com/TeKrop/overfast-api/pull/249),
  [`9f68669`](https://github.com/TeKrop/overfast-api/commit/9f68669718dcbd20108c39085ef914f8b68ef7dd))


## v3.11.2 (2025-04-27)

### Features

- Using OverFastClient within UnlocksManager
  ([#248](https://github.com/TeKrop/overfast-api/pull/248),
  [`2db4128`](https://github.com/TeKrop/overfast-api/commit/2db412840e8d936d5384302666ef8ac9c7ab7193))


## v3.11.1 (2025-04-26)

### Features

- Added Stadium-exclusive maps ([#247](https://github.com/TeKrop/overfast-api/pull/247),
  [`0fbac17`](https://github.com/TeKrop/overfast-api/commit/0fbac17db7e1a8093ff75274b88bc74404a8a162))


## v3.11.0 (2025-04-26)

### Build System

- **deps**: Bump pydantic-settings from 2.8.1 to 2.9.1
  ([#242](https://github.com/TeKrop/overfast-api/pull/242),
  [`07afa93`](https://github.com/TeKrop/overfast-api/commit/07afa93fd19a4fc66308c16cb4a1e28181042356))

### Features

- Added support for unlocks data after Blizzard breaking changes
  ([#246](https://github.com/TeKrop/overfast-api/pull/246),
  [`80b63f9`](https://github.com/TeKrop/overfast-api/commit/80b63f91900c4f2ae48bdae579e9d9171c946ef3))


## v3.10.4 (2025-04-14)

### Build System

- **deps**: Bump pydantic from 2.10.6 to 2.11.2
  ([#239](https://github.com/TeKrop/overfast-api/pull/239),
  [`ab240d2`](https://github.com/TeKrop/overfast-api/commit/ab240d28fa118353652379503287fdb01900d71a))

- **deps**: Bump selectolax from 0.3.27 to 0.3.28
  ([#235](https://github.com/TeKrop/overfast-api/pull/235),
  [`971fa17`](https://github.com/TeKrop/overfast-api/commit/971fa17f25f78c594146a212915b838172062f1a))

- **deps**: Update pydantic-settings requirement
  ([#233](https://github.com/TeKrop/overfast-api/pull/233),
  [`fbe5505`](https://github.com/TeKrop/overfast-api/commit/fbe5505ca982bc8ac7366ef634e2c94dffe56694))

### Features

- Updated dev dependencies ([#241](https://github.com/TeKrop/overfast-api/pull/241),
  [`69e08ea`](https://github.com/TeKrop/overfast-api/commit/69e08eaec4bb1761e5f2a6c6be5d1e36c0cee616))


## v3.10.3 (2025-04-07)

### Bug Fixes

- Fixed issue with invalid html format when player not found
  ([#240](https://github.com/TeKrop/overfast-api/pull/240),
  [`4237155`](https://github.com/TeKrop/overfast-api/commit/423715545ae97c1bcc64869e9f6f0131e53a1df6))


## v3.10.2 (2025-03-29)

### Bug Fixes

- Fixed issue on heroes pages for es-mx and ko-kr locales
  ([#237](https://github.com/TeKrop/overfast-api/pull/237),
  [`af79d10`](https://github.com/TeKrop/overfast-api/commit/af79d10af0722726e40c4c3d60415b11b3b59234))

### Features

- Updated heroes data ([#236](https://github.com/TeKrop/overfast-api/pull/236),
  [`af920f6`](https://github.com/TeKrop/overfast-api/commit/af920f679ec3d704a492b2f133dbafdcf3c49166))


## v3.10.1 (2025-03-11)

### Bug Fixes

- Fixed issue with some profiles having empty select
  ([#234](https://github.com/TeKrop/overfast-api/pull/234),
  [`8e03aa6`](https://github.com/TeKrop/overfast-api/commit/8e03aa6d59b6d051d6d56d83d2dce2ccef519cdb))


## v3.10.0 (2025-03-08)

### Features

- Added setting to disable discord message on rate limit
  ([#232](https://github.com/TeKrop/overfast-api/pull/232),
  [`9c9c115`](https://github.com/TeKrop/overfast-api/commit/9c9c11562f992fcb75de72c51ad37d5e7e0f9aa1))


## v3.9.4 (2025-03-04)

### Bug Fixes

- Added proper support for remote protocol error from Blizzard
  ([#231](https://github.com/TeKrop/overfast-api/pull/231),
  [`bade464`](https://github.com/TeKrop/overfast-api/commit/bade464e0e8953267e805a5e167919378a7fabd1))


## v3.9.3 (2025-02-15)

### Features

- Added support for Freja ([#229](https://github.com/TeKrop/overfast-api/pull/229),
  [`06a26ed`](https://github.com/TeKrop/overfast-api/commit/06a26ed14f7a6f78cfe73cc40b7cfd5b633cb9eb))


## v3.9.2 (2025-02-04)

### Features

- Updated dependencies ([#228](https://github.com/TeKrop/overfast-api/pull/228),
  [`db7de76`](https://github.com/TeKrop/overfast-api/commit/db7de7611d8e334aa2104473e4989bb5279d6b6b))


## v3.9.1 (2025-02-02)

### Bug Fixes

- **encoding**: Forcing ascii chars in app response body
  ([#227](https://github.com/TeKrop/overfast-api/pull/227),
  [`f0f4aab`](https://github.com/TeKrop/overfast-api/commit/f0f4aab7de5460df1287dfc37316f10e75e408d5))


## v3.9.0 (2025-01-04)

### Features

- Added support for btag on players search endpoints. updated dependencies
  ([#225](https://github.com/TeKrop/overfast-api/pull/225),
  [`cfe7e32`](https://github.com/TeKrop/overfast-api/commit/cfe7e3279b5ed5c650e57d60571e93d555ddd8d1))


## v3.8.2 (2025-01-01)

### Bug Fixes

- Using entire btag with encoded number sign for players search
  ([#224](https://github.com/TeKrop/overfast-api/pull/224),
  [`6871d2d`](https://github.com/TeKrop/overfast-api/commit/6871d2da7d15c6d0efa91bef328125c2b362181f))


## v3.8.1 (2024-12-15)


## v3.8.0 (2024-11-26)

### Features

- Improved caching memory usage ([#221](https://github.com/TeKrop/overfast-api/pull/221),
  [`62c77bd`](https://github.com/TeKrop/overfast-api/commit/62c77bdc15c1757827627e721a054cfe22b41f3f))


## v3.7.0 (2024-11-24)

### Features

- Added support for TTL in response headers
  ([#219](https://github.com/TeKrop/overfast-api/pull/219),
  [`24df519`](https://github.com/TeKrop/overfast-api/commit/24df519ff6c067c9d6cfdf44fdd03573ed4d0a57))


## v3.6.1 (2024-11-23)


## v3.6.0 (2024-11-21)

### Features

- Added hazard hero in list ([#217](https://github.com/TeKrop/overfast-api/pull/217),
  [`732e771`](https://github.com/TeKrop/overfast-api/commit/732e77166e193237c976bbf11adcb071bd6c47d7))


## v3.5.1 (2024-11-12)

### Bug Fixes

- Fixed parsing after blizzard change of main div
  ([#216](https://github.com/TeKrop/overfast-api/pull/216),
  [`9baecbe`](https://github.com/TeKrop/overfast-api/commit/9baecbee719e41fdbbdccde608994f3b823879d7))


## v3.5.0 (2024-11-10)

### Features

- Refactored tests to make them easier to maintain
  ([#215](https://github.com/TeKrop/overfast-api/pull/215),
  [`20341ed`](https://github.com/TeKrop/overfast-api/commit/20341ed640e9a3a25711472024df07060ff4ca93))


## v3.4.0 (2024-11-09)

### Features

- Updated to python 3.13 and uv 5.1 ([#214](https://github.com/TeKrop/overfast-api/pull/214),
  [`46ed1f0`](https://github.com/TeKrop/overfast-api/commit/46ed1f02c4de45a156f928abdcad853ca99ef82a))


## v3.3.0 (2024-11-09)

### Features

- Replaced Beautiful Soup by selectolax to enhance performance
  ([#213](https://github.com/TeKrop/overfast-api/pull/213),
  [`9916b04`](https://github.com/TeKrop/overfast-api/commit/9916b04a8cd643eba2a9843e5187baa3bd6c31c2))

- Updated gh actions versions ([#212](https://github.com/TeKrop/overfast-api/pull/212),
  [`7e60c1d`](https://github.com/TeKrop/overfast-api/commit/7e60c1de9ab95260e9ab28309a3686674377f00d))


## v3.2.1 (2024-11-07)

### Bug Fixes

- Fixed memory leak and added more profiling middlewares
  ([#211](https://github.com/TeKrop/overfast-api/pull/211),
  [`da6d501`](https://github.com/TeKrop/overfast-api/commit/da6d5019e7e47f5156bf57026eda53a5a2b2ed1b))


## v3.2.0 (2024-11-05)

### Features

- Optimized performances on player profiles parsing
  ([#210](https://github.com/TeKrop/overfast-api/pull/210),
  [`9a602d0`](https://github.com/TeKrop/overfast-api/commit/9a602d0a845be54553939543b49a25093ba3041f))


## v3.1.0 (2024-11-04)

### Features

- Added gamemode and platform filtering on all player data endpoint
  ([#209](https://github.com/TeKrop/overfast-api/pull/209),
  [`6620eaa`](https://github.com/TeKrop/overfast-api/commit/6620eaa8f2890b35a2fe8885525bd3b415fa9b12))


## v3.0.0 (2024-11-03)

### Features

- OverFast API v3 ([#208](https://github.com/TeKrop/overfast-api/pull/208),
  [`7d24e14`](https://github.com/TeKrop/overfast-api/commit/7d24e14ead7cd74a419759251577c09296e57c83))


## v2.40.1 (2024-10-26)

### Features

- Updated dependencies ([#206](https://github.com/TeKrop/overfast-api/pull/206),
  [`2977674`](https://github.com/TeKrop/overfast-api/commit/2977674dd4e6a954389f51826be167f0428d5e6d))


## v2.40.0 (2024-10-26)

### Features

- Added configurable rate limiting system ([#205](https://github.com/TeKrop/overfast-api/pull/205),
  [`b8f66de`](https://github.com/TeKrop/overfast-api/commit/b8f66dedaff935d16cc344cb7a5ecef6de8ef940))


## v2.39.0 (2024-10-17)

### Features

- Enhanced nginx settings ([#203](https://github.com/TeKrop/overfast-api/pull/203),
  [`332f684`](https://github.com/TeKrop/overfast-api/commit/332f684eeaa01697233d0de8ecc4a734de197a66))


## v2.38.0 (2024-10-15)

### Features

- Added possibility to toggle background cache system
  ([#202](https://github.com/TeKrop/overfast-api/pull/202),
  [`7c6b6a3`](https://github.com/TeKrop/overfast-api/commit/7c6b6a3e3dc02356bf51c916020f71b9657dbbf2))


## v2.37.2 (2024-10-12)

### Features

- Updated dependencies ([#200](https://github.com/TeKrop/overfast-api/pull/200),
  [`96cd53e`](https://github.com/TeKrop/overfast-api/commit/96cd53e8baf094f1f389bff3085c99764e2b6b8a))


## v2.37.1 (2024-09-15)

### Bug Fixes

- Fixed issue with missing chapter content on Juno hero page
  ([#195](https://github.com/TeKrop/overfast-api/pull/195),
  [`5e9d333`](https://github.com/TeKrop/overfast-api/commit/5e9d3330b500aa277b1b9eab618db2c9804c7c48))


## v2.37.0 (2024-09-12)

### Features

- Added clash mode and associated maps ([#193](https://github.com/TeKrop/overfast-api/pull/193),
  [`95e23fc`](https://github.com/TeKrop/overfast-api/commit/95e23fc874766a303d5ef79220122852a62cdfd7))

- Updated uv to v0.4.5 ([#189](https://github.com/TeKrop/overfast-api/pull/189),
  [`04eca3e`](https://github.com/TeKrop/overfast-api/commit/04eca3e68910f6ac911bb95bb7103b7dc34546ea))


## v2.36.0 (2024-09-04)

### Features

- Enhanced async client usage ([#187](https://github.com/TeKrop/overfast-api/pull/187),
  [`94a0299`](https://github.com/TeKrop/overfast-api/commit/94a02998608c1444d36ae6f4786788652b23ca61))


## v2.35.2 (2024-08-29)

### Features

- Updated uv to 0.4.0 and adjusted config accordingly
  ([#186](https://github.com/TeKrop/overfast-api/pull/186),
  [`051aaee`](https://github.com/TeKrop/overfast-api/commit/051aaee5405b153c99181af6c5be1fee95ffccbe))


## v2.35.1 (2024-08-27)

### Bug Fixes

- Fixed an issue with LastUpdatedAt cache refresh
  ([#185](https://github.com/TeKrop/overfast-api/pull/185),
  [`875d506`](https://github.com/TeKrop/overfast-api/commit/875d5068239cf7e5e89f8365c4d7833a31226d80))


## v2.35.0 (2024-08-25)

### Features

- Added last_updated_at in players search results and player summary
  ([#184](https://github.com/TeKrop/overfast-api/pull/184),
  [`9325b4f`](https://github.com/TeKrop/overfast-api/commit/9325b4fe8948564df1d6b55266b62dde9600b06a))


## v2.34.1 (2024-08-24)

### Features

- Updated dependencies to last version ([#183](https://github.com/TeKrop/overfast-api/pull/183),
  [`f9d17e4`](https://github.com/TeKrop/overfast-api/commit/f9d17e47b590aa364678aa8f976f8f867a9d85d0))


## v2.34.0 (2024-08-24)

### Build System

- **deps**: Bump fastapi from 0.111.1 to 0.112.0
  ([#172](https://github.com/TeKrop/overfast-api/pull/172),
  [`cd64305`](https://github.com/TeKrop/overfast-api/commit/cd643052584d976ace34e26f27c2928e45612d67))

- **deps**: Bump fastapi from 0.112.0 to 0.112.1
  ([#180](https://github.com/TeKrop/overfast-api/pull/180),
  [`3c99216`](https://github.com/TeKrop/overfast-api/commit/3c992169936eef3a18574a13797ce79d7fcbb7af))

- **deps**: Bump lxml from 5.2.2 to 5.3.0 ([#178](https://github.com/TeKrop/overfast-api/pull/178),
  [`d169870`](https://github.com/TeKrop/overfast-api/commit/d1698703cacb203fb210c51eb78b9573e6c8d64f))

- **deps**: Bump pydantic-settings from 2.3.4 to 2.4.0
  ([#173](https://github.com/TeKrop/overfast-api/pull/173),
  [`a69bb31`](https://github.com/TeKrop/overfast-api/commit/a69bb318bbd2f35b877ca46c206c4e1f12e7b2d5))

- **deps**: Bump redis from 5.0.7 to 5.0.8 ([#175](https://github.com/TeKrop/overfast-api/pull/175),
  [`8c76424`](https://github.com/TeKrop/overfast-api/commit/8c764242737952ee93484f9655433e68ef6026bf))

- **deps-dev**: Bump fakeredis from 2.23.3 to 2.23.5
  ([#176](https://github.com/TeKrop/overfast-api/pull/176),
  [`0fb0b26`](https://github.com/TeKrop/overfast-api/commit/0fb0b26198bb25369390c21b8416ef0162700afc))

- **deps-dev**: Bump ruff from 0.5.5 to 0.5.6
  ([#174](https://github.com/TeKrop/overfast-api/pull/174),
  [`88564b8`](https://github.com/TeKrop/overfast-api/commit/88564b8c50be341d5455783a2353b103e1b6fea6))

- **deps-dev**: Bump ruff from 0.5.6 to 0.5.7
  ([#179](https://github.com/TeKrop/overfast-api/pull/179),
  [`4a24577`](https://github.com/TeKrop/overfast-api/commit/4a24577db64ae1ec7ac69ffe8634538b9698b301))

### Features

- Replaced poetry with uv ([#182](https://github.com/TeKrop/overfast-api/pull/182),
  [`842a684`](https://github.com/TeKrop/overfast-api/commit/842a684e8404f6dd0c868fbdfcdb463fcd45cc9f))


## v2.33.1 (2024-08-02)

### Bug Fixes

- Fixed unsupported big float values ([#171](https://github.com/TeKrop/overfast-api/pull/171),
  [`f466a43`](https://github.com/TeKrop/overfast-api/commit/f466a43f076fbe14f7b627a6aa322d5f56b6c07c))

### Build System

- **deps-dev**: Bump pre-commit from 3.7.1 to 3.8.0
  ([#168](https://github.com/TeKrop/overfast-api/pull/168),
  [`40d067a`](https://github.com/TeKrop/overfast-api/commit/40d067aa35e9d0e40cf3f1f3aad2c1f60b78a803))

- **deps-dev**: Bump pytest from 8.3.1 to 8.3.2
  ([#169](https://github.com/TeKrop/overfast-api/pull/169),
  [`1017398`](https://github.com/TeKrop/overfast-api/commit/101739877ec6f780f8eb930119c2804105b94623))

- **deps-dev**: Bump ruff from 0.5.4 to 0.5.5
  ([#170](https://github.com/TeKrop/overfast-api/pull/170),
  [`91451e4`](https://github.com/TeKrop/overfast-api/commit/91451e4533858dd4fcd493560c2d51981c686f27))


## v2.33.0 (2024-07-27)


## v2.32.1 (2024-07-27)

### Bug Fixes

- Fixed two issues with Blizzard profiles ([#166](https://github.com/TeKrop/overfast-api/pull/166),
  [`6b68612`](https://github.com/TeKrop/overfast-api/commit/6b68612321b0842a38b2d638cfe36f75618149ab))

### Build System

- **deps-dev**: Bump pytest from 8.2.2 to 8.3.1
  ([#165](https://github.com/TeKrop/overfast-api/pull/165),
  [`b6a23f0`](https://github.com/TeKrop/overfast-api/commit/b6a23f0cb9c334f9d765e3e9ec803878ec0fb8b1))

- **deps-dev**: Bump pytest-asyncio from 0.23.7 to 0.23.8
  ([#163](https://github.com/TeKrop/overfast-api/pull/163),
  [`e403d82`](https://github.com/TeKrop/overfast-api/commit/e403d82785e99c43afaec00f052a14bdb605abd0))

- **deps-dev**: Bump ruff from 0.5.2 to 0.5.4
  ([#164](https://github.com/TeKrop/overfast-api/pull/164),
  [`6fadcdb`](https://github.com/TeKrop/overfast-api/commit/6fadcdb4f04d34581db57e6b7c2d4b41d8db3e4e))


## v2.32.0 (2024-07-19)

### Build System

- **deps**: Bump certifi from 2024.2.2 to 2024.7.4 in the pip group
  ([#156](https://github.com/TeKrop/overfast-api/pull/156),
  [`b2e16d5`](https://github.com/TeKrop/overfast-api/commit/b2e16d5c9669024d81e30cd4fb9c42dc64be5ae9))

- **deps**: Bump fastapi from 0.111.0 to 0.111.1
  ([#159](https://github.com/TeKrop/overfast-api/pull/159),
  [`27996c3`](https://github.com/TeKrop/overfast-api/commit/27996c334f1c28d0038aaf7a1ac86c258694f3e5))

- **deps**: Bump pydantic from 2.7.4 to 2.8.2
  ([#158](https://github.com/TeKrop/overfast-api/pull/158),
  [`7463446`](https://github.com/TeKrop/overfast-api/commit/74634467929cb312cd71f6bb88d94e950a40cb3f))

- **deps-dev**: Bump ruff from 0.5.0 to 0.5.1
  ([#157](https://github.com/TeKrop/overfast-api/pull/157),
  [`d53ebcd`](https://github.com/TeKrop/overfast-api/commit/d53ebcd760eb1a3ae819460b65f9708fc633f86c))

- **deps-dev**: Bump ruff from 0.5.1 to 0.5.2
  ([#160](https://github.com/TeKrop/overfast-api/pull/160),
  [`4d8b7e1`](https://github.com/TeKrop/overfast-api/commit/4d8b7e14f1a4718f6dad0bd9c76faa7ca6349aa4))

- **deps-dev**: Bump setuptools from 69.5.1 to 70.0.0 in the pip group
  ([#161](https://github.com/TeKrop/overfast-api/pull/161),
  [`2ea133c`](https://github.com/TeKrop/overfast-api/commit/2ea133c91bddabc7f555eac7fa38c0bb679cb184))

### Features

- Added HTTP 429 response doc if option is enabled
  ([#155](https://github.com/TeKrop/overfast-api/pull/155),
  [`d48b104`](https://github.com/TeKrop/overfast-api/commit/d48b10486c9b3682489157511ba7744217204ff4))

- Added support for Juno. Updated heroes data.
  ([#162](https://github.com/TeKrop/overfast-api/pull/162),
  [`e9d872c`](https://github.com/TeKrop/overfast-api/commit/e9d872c7d7ca6c0a3022ae27deb41e0090455caa))


## v2.31.0 (2024-07-01)

### Build System

- **deps**: Bump pydantic-settings from 2.3.3 to 2.3.4
  ([#152](https://github.com/TeKrop/overfast-api/pull/152),
  [`cb508c9`](https://github.com/TeKrop/overfast-api/commit/cb508c9cad83bb2b0edd761cd28b7aa2ad96a8d2))

- **deps**: Bump redis from 5.0.6 to 5.0.7 ([#151](https://github.com/TeKrop/overfast-api/pull/151),
  [`ed9c825`](https://github.com/TeKrop/overfast-api/commit/ed9c825f218ab030c65c468d9b8372ab65ded582))

- **deps-dev**: Bump fakeredis from 2.23.2 to 2.23.3
  ([#153](https://github.com/TeKrop/overfast-api/pull/153),
  [`331946d`](https://github.com/TeKrop/overfast-api/commit/331946df0866e6a2ff93588ab9b07e52fd3b69a5))

- **deps-dev**: Bump ruff from 0.4.10 to 0.5.0
  ([#150](https://github.com/TeKrop/overfast-api/pull/150),
  [`63e720e`](https://github.com/TeKrop/overfast-api/commit/63e720e4c3ffb11a39f4fda69a9c6d9980ada751))

### Features

- Add Runasapi to maps and test ([#149](https://github.com/TeKrop/overfast-api/pull/149),
  [`f9cb0af`](https://github.com/TeKrop/overfast-api/commit/f9cb0afc56172122552dfeae9f7a0d962f2ecf74))


## v2.30.0 (2024-06-24)

### Build System

- **deps-dev**: Bump ruff from 0.4.9 to 0.4.10
  ([#147](https://github.com/TeKrop/overfast-api/pull/147),
  [`374711b`](https://github.com/TeKrop/overfast-api/commit/374711bef5dcb73d8ca93355fd540c3d18ba9351))

### Features

- Updated nginx version to latest, and using custom ngx_http_redis version with fix for nginx >=
  1.23 ([#146](https://github.com/TeKrop/overfast-api/pull/146),
  [`e9cdf0e`](https://github.com/TeKrop/overfast-api/commit/e9cdf0e562d4315698bf777d6980bf8d6e3291c5))


## v2.29.4 (2024-06-23)

### Bug Fixes

- Fixed issue with roles endpoint since Blizzard update
  ([#145](https://github.com/TeKrop/overfast-api/pull/145),
  [`e6fd7b8`](https://github.com/TeKrop/overfast-api/commit/e6fd7b891de8bacf4192a88ee280e019bad795a6))


## v2.29.3 (2024-06-20)

### Bug Fixes

- Updated api parser after last Blizzard pages update
  ([#144](https://github.com/TeKrop/overfast-api/pull/144),
  [`7b01ba1`](https://github.com/TeKrop/overfast-api/commit/7b01ba1f47e16faafb1f24abbd5027618a703a5c))

### Build System

- **deps**: Bump pydantic from 2.7.3 to 2.7.4
  ([#139](https://github.com/TeKrop/overfast-api/pull/139),
  [`9eae4ed`](https://github.com/TeKrop/overfast-api/commit/9eae4ed825c6da1892db651b3432fac4461a35d0))

- **deps**: Bump pydantic-settings from 2.3.1 to 2.3.3
  ([#141](https://github.com/TeKrop/overfast-api/pull/141),
  [`c47cf8b`](https://github.com/TeKrop/overfast-api/commit/c47cf8b45094af422a86673c4a4b31b048011c42))

- **deps**: Bump redis from 5.0.5 to 5.0.6 ([#140](https://github.com/TeKrop/overfast-api/pull/140),
  [`17983a9`](https://github.com/TeKrop/overfast-api/commit/17983a9136044b2c8c81cb90fc0ede7d1183b9c1))

- **deps-dev**: Bump ruff from 0.4.8 to 0.4.9
  ([#138](https://github.com/TeKrop/overfast-api/pull/138),
  [`32fe549`](https://github.com/TeKrop/overfast-api/commit/32fe5495600441f0180da35e396345e10c4ba2a9))


## v2.29.2 (2024-06-12)

### Build System

- **deps**: Bump pydantic from 2.7.2 to 2.7.3
  ([#135](https://github.com/TeKrop/overfast-api/pull/135),
  [`dd1c13b`](https://github.com/TeKrop/overfast-api/commit/dd1c13bf151303f699a8ae5bf1828668d843f134))

- **deps**: Bump pydantic-settings from 2.2.1 to 2.3.1
  ([#134](https://github.com/TeKrop/overfast-api/pull/134),
  [`0c37c3f`](https://github.com/TeKrop/overfast-api/commit/0c37c3fd674b0c68034958d1898b98257729a6a4))

- **deps**: Bump redis from 5.0.4 to 5.0.5 ([#132](https://github.com/TeKrop/overfast-api/pull/132),
  [`5320ec9`](https://github.com/TeKrop/overfast-api/commit/5320ec9b3af01080f8c68b280ddb2d50070b6d94))

- **deps-dev**: Bump pytest from 8.2.1 to 8.2.2
  ([#133](https://github.com/TeKrop/overfast-api/pull/133),
  [`79d25b6`](https://github.com/TeKrop/overfast-api/commit/79d25b62d8642660c1b96740ff3b94c082765a89))

- **deps-dev**: Bump ruff from 0.4.7 to 0.4.8
  ([#136](https://github.com/TeKrop/overfast-api/pull/136),
  [`9169bbf`](https://github.com/TeKrop/overfast-api/commit/9169bbffc8ed2ca0b714c2fec9699c5c8baa4a3b))

### Features

- Now building ngx_http_redis_module.so on nginx image build
  ([#137](https://github.com/TeKrop/overfast-api/pull/137),
  [`037fc09`](https://github.com/TeKrop/overfast-api/commit/037fc0906d536a3c2c47620bdafdf78f4a8e58a4))


## v2.29.1 (2024-06-09)

### Build System

- **deps**: Bump pydantic from 2.7.1 to 2.7.2
  ([#128](https://github.com/TeKrop/overfast-api/pull/128),
  [`203b5b7`](https://github.com/TeKrop/overfast-api/commit/203b5b7fe27b98012a3ba2f4def54cae2f630c6e))

- **deps-dev**: Bump ruff from 0.4.4 to 0.4.5
  ([#127](https://github.com/TeKrop/overfast-api/pull/127),
  [`1ae0637`](https://github.com/TeKrop/overfast-api/commit/1ae063775bd842df7867bb313b49293d342ef17a))

- **deps-dev**: Bump ruff from 0.4.5 to 0.4.7
  ([#129](https://github.com/TeKrop/overfast-api/pull/129),
  [`32e763e`](https://github.com/TeKrop/overfast-api/commit/32e763ec289c98ad97dbf92086a1a7a3b4f63755))


## v2.29.0 (2024-05-20)

### Bug Fixes

- Fixed an issue with roles page after Blizzard update
  ([#126](https://github.com/TeKrop/overfast-api/pull/126),
  [`becf032`](https://github.com/TeKrop/overfast-api/commit/becf03265b1482be54af3356ec96a66e00ebf389))

### Build System

- **deps-dev**: Bump fakeredis from 2.23.1 to 2.23.2
  ([#124](https://github.com/TeKrop/overfast-api/pull/124),
  [`7bb94fe`](https://github.com/TeKrop/overfast-api/commit/7bb94fec1be02c61af0b2d4f39b78cd2af31960d))

- **deps-dev**: Bump pytest from 8.2.0 to 8.2.1
  ([#123](https://github.com/TeKrop/overfast-api/pull/123),
  [`e944721`](https://github.com/TeKrop/overfast-api/commit/e944721227b1296de4dc845b6221b46f51ec5b56))

- **deps-dev**: Bump pytest-asyncio from 0.23.6 to 0.23.7
  ([#125](https://github.com/TeKrop/overfast-api/pull/125),
  [`80d1876`](https://github.com/TeKrop/overfast-api/commit/80d18765422ce442a895a2e0dd31afe66b99026d))

### Features

- Build system update ([#113](https://github.com/TeKrop/overfast-api/pull/113),
  [`945cc77`](https://github.com/TeKrop/overfast-api/commit/945cc7748b940df92cc5f770cc23f4e97eb9b511))

- Updated fastapi and using fastapi-cli for dev/prod
  ([#118](https://github.com/TeKrop/overfast-api/pull/118),
  [`c6dc164`](https://github.com/TeKrop/overfast-api/commit/c6dc164dccc88bd9ec639448e86eb207ef956927))


## v2.28.1 (2024-04-18)

### Bug Fixes

- Fixed age and birthday support for all locales
  ([#111](https://github.com/TeKrop/overfast-api/pull/111),
  [`87673db`](https://github.com/TeKrop/overfast-api/commit/87673db63abc6aa1424abc85b6f1574b5e79603e))


## v2.28.0 (2024-04-16)


## v2.27.1 (2024-04-11)

### Features

- Apply S9 health pool ([#108](https://github.com/TeKrop/overfast-api/pull/108),
  [`45d5d57`](https://github.com/TeKrop/overfast-api/commit/45d5d5734f90228eb1865f40190e9605c3d28583))


## v2.27.0 (2024-03-30)

### Features

- Added Makefile to run local commands
  ([`01c0a6d`](https://github.com/TeKrop/overfast-api/commit/01c0a6d6459255ebe9eb74798fe0b915c4f91023))

- Now using docker for dev with dedicated makefile
  ([#107](https://github.com/TeKrop/overfast-api/pull/107),
  [`4f1ffd4`](https://github.com/TeKrop/overfast-api/commit/4f1ffd4080de715e3ea22a5bd6c6270ea45ddede))


## v2.26.0 (2024-02-22)

### Features

- Adding Blizzard ID to the search JSON ([#98](https://github.com/TeKrop/overfast-api/pull/98),
  [`f5108d2`](https://github.com/TeKrop/overfast-api/commit/f5108d2f059c3c845e5a59f4b31fac3090ad249b))


## v2.25.2 (2024-02-20)

### Features

- Made status page URL configurable and added description about live instance rate limits
  ([#97](https://github.com/TeKrop/overfast-api/pull/97),
  [`43cf8a1`](https://github.com/TeKrop/overfast-api/commit/43cf8a1bc343ca8fcf9bd62a41c5fa2d2cf4c834))


## v2.25.1 (2024-02-14)

### Bug Fixes

- Fixed support for champion rank (ultimate) ([#95](https://github.com/TeKrop/overfast-api/pull/95),
  [`d56fd30`](https://github.com/TeKrop/overfast-api/commit/d56fd30cfd7e4c28ab45f794b11361eba6ef2e28))


## v2.25.0 (2024-02-14)

### Bug Fixes

- Fixed issues after Blizzard update and mostly update competitive informations
  ([#93](https://github.com/TeKrop/overfast-api/pull/93),
  [`24a321f`](https://github.com/TeKrop/overfast-api/commit/24a321ff03fe868d1b67653a145ea0d50f48fc52))


## v2.24.0 (2024-01-02)


## v2.23.1 (2023-12-22)

### Bug Fixes

- Fixed an issue when a player played on season 0in Blizzard data. Updated Mauga data following
  patch notes. ([#80](https://github.com/TeKrop/overfast-api/pull/80),
  [`04cfcba`](https://github.com/TeKrop/overfast-api/commit/04cfcbabf59c578d428fedbd8e938a13fa2bd63d))


## v2.23.0 (2023-12-06)

### Bug Fixes

- Fixed issue with new big numbers format on Blizzard stats. Updated heroes data.
  ([#79](https://github.com/TeKrop/overfast-api/pull/79),
  [`5002fc0`](https://github.com/TeKrop/overfast-api/commit/5002fc043713181c52f51b3007ce874cbb7aa81c))


## v2.22.1 (2023-11-05)

### Features

- Updated Mauga data and added preemptive support for Venture
  ([`810e617`](https://github.com/TeKrop/overfast-api/commit/810e6172dd84690843c74ab7b30131447bc366cd))


## v2.22.0 (2023-11-04)

### Features

- Added support for Mauga ([#76](https://github.com/TeKrop/overfast-api/pull/76),
  [`eac6127`](https://github.com/TeKrop/overfast-api/commit/eac612789c8ffdaa73bb77c5f2f9263ff95b18d1))

- Updated project to use python 3.12 ([#75](https://github.com/TeKrop/overfast-api/pull/75),
  [`e806554`](https://github.com/TeKrop/overfast-api/commit/e80655457dfed08562924acd5d6561b75dd3cdf1))


## v2.21.0 (2023-11-01)

### Features

- Updated flashpoint with official data. updated heroes data from last update.
  ([#74](https://github.com/TeKrop/overfast-api/pull/74),
  [`cd52977`](https://github.com/TeKrop/overfast-api/commit/cd529772809e6448eb5aa7cf62a606ea930be51e))


## v2.20.2 (2023-11-01)

### Bug Fixes

- Issue with player profiles without title ingame
  ([#73](https://github.com/TeKrop/overfast-api/pull/73),
  [`6ea8315`](https://github.com/TeKrop/overfast-api/commit/6ea8315101da730b68bb595631796914ce546553))

### Features

- Bump version in pyproject.toml
  ([`0607123`](https://github.com/TeKrop/overfast-api/commit/06071239f01af25885a7de08b9a661bc28cf19d5))


## v2.20.1 (2023-10-25)

### Bug Fixes

- Fixed an issue with new icon url for roles ([#69](https://github.com/TeKrop/overfast-api/pull/69),
  [`c4b8908`](https://github.com/TeKrop/overfast-api/commit/c4b8908f3603ee7327746bcc9d74cb79c5931781))

- Updated email information
  ([`83ca658`](https://github.com/TeKrop/overfast-api/commit/83ca658c29a312e15d66af76ef2c46255ed8531e))


## v2.20.0 (2023-10-11)

### Bug Fixes

- Updated tests after dependencies update
  ([`daffc8e`](https://github.com/TeKrop/overfast-api/commit/daffc8e30e71a01124c90c67922d77f21eaefaa8))

### Features

- Added Samoa map ([#67](https://github.com/TeKrop/overfast-api/pull/67),
  [`8c49d11`](https://github.com/TeKrop/overfast-api/commit/8c49d1155adf00cfb3393070b332ef56f50ea7a4))


## v2.19.4 (2023-09-02)


## v2.19.3 (2023-08-13)


## v2.19.2 (2023-08-11)


## v2.19.1 (2023-08-09)


## v2.19.0 (2023-08-07)


## v2.18.0 (2023-08-06)


## v2.17.2 (2023-06-17)


## v2.17.1 (2023-05-28)


## v2.17.0 (2023-05-27)


## v2.16.0 (2023-05-21)


## v2.15.1 (2023-05-09)


## v2.15.0 (2023-05-04)


## v2.14.0 (2023-04-19)


## v2.13.1 (2023-04-18)


## v2.13.0 (2023-04-04)


## v2.12.0 (2023-03-29)


## v2.11.1 (2023-03-25)


## v2.11.0 (2023-03-21)


## v2.10.0 (2023-03-12)


## v2.9.0 (2023-03-05)


## v2.8.3 (2023-03-05)


## v2.8.2 (2023-02-27)


## v2.8.1 (2023-02-25)


## v2.8.0 (2023-02-22)


## v2.7.2 (2023-02-19)


## v2.7.1 (2023-02-13)


## v2.7.0 (2023-01-29)


## v2.6.0 (2023-01-25)


## v2.5.0 (2023-01-23)


## v2.4.0 (2023-01-08)


## v2.3.4 (2023-01-03)


## v2.3.3 (2022-12-19)


## v2.3.2 (2022-12-11)


## v2.3.1 (2022-12-09)


## v2.3.0 (2022-12-08)


## v2.2.0 (2022-12-06)


## v2.1.1 (2022-11-19)


## v2.1.0 (2022-11-19)


## v2.0.3 (2022-10-31)


## v2.0.2 (2022-10-28)


## v2.0.1 (2022-10-09)


## v2.0.0 (2022-10-09)

- Initial Release
