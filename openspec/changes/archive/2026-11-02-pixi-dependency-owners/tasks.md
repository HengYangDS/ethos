# Tasks

## 1. Owner

- [x] 1.1 Read the Pixi manifest as a declaration and let each conda dependency own the executable of
      its package name. Done when `pip = "*"` in `[feature.host.dependencies]` admits a touched guide
      that runs `pip install`, a `[tool.pixi.dependencies]` entry does the same without a
      `pixi.toml`, and `pip3`, a PyPI dependency and a `[constraints]` entry stay refused. (The four
      owner cases and the admission case pass; on di-effect's head `ae3d9ab43` a touched onboarding
      guide now refuses only `brew`.)

## 2. Specification

- [x] 2.1 Write the `repository-governance` delta. Done when strict validation and the cumulative
      archive simulation pass. (12 of 12 specs valid after the three simulated archives.)

## Workflow follow-up

- Before landing, the GitHub and GitLab runs of the proposal at the lane's last code commit pass.
