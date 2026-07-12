# Home Assistant Smart-Home Setup

This guide is the practical rollout path for Mia smart-home control on the current stack.

## Target shape

- Home Assistant runs locally in Docker on the same machine.
- Google Home can stay as the daily voice interface.
- Mia uses Home Assistant as the safe control hub.
- Only entities labeled `mia_allowed` are visible to Mia.
- Clear commands should execute immediately; ambiguous commands should ask back.

## Current local endpoints

- Home Assistant dashboard: `http://192.168.1.91:8123`
- Mia core health: `http://127.0.0.1:8000/health`
- n8n local UI: `http://127.0.0.1:5678`

## Recommended integration order

1. Finish Home Assistant onboarding in the browser.
2. Add vendor integrations directly in Home Assistant:
   - Tuya
   - Xiaomi
   - Google Cast
3. Put devices into real Areas first.
4. Add the `mia_allowed` label only to devices Mia may control.
5. Create a Long-Lived Access Token for n8n.
6. Save that token into `HOME_ASSISTANT_TOKEN` in `.env`.
7. Restart `n8n` and `mia-core`.

## Suggested area layout for the current home

- `Phòng ngủ`
- `Phòng tắm`
- Optional later:
  - `Bàn làm việc`
  - `Phòng khách`
  - `Ban công`

## Suggested entity naming pattern

Keep names short, stable, and room-aware:

- `Đèn phòng ngủ`
- `Đèn phòng tắm`
- `Công tắc PC`
- `Máy lạnh phòng ngủ`
- `Quạt phòng ngủ`
- `Máy lọc không khí phòng ngủ`
- `Loa phòng ngủ`

This naming style makes the alias generator produce cleaner suggestions.

## What Mia can already do

- List visible rooms
- List visible devices
- Read room status
- Turn one device on or off
- Toggle a device
- Change light brightness or color temperature
- Change climate mode or target temperature
- Change fan speed or preset
- Control a media player
- Run a Home Assistant scene
- Run a Home Assistant script
- Speak a TTS message if `MIA_HOME_TTS_ENTITY_ID` is set

## Token and inventory bootstrap

After Home Assistant is onboarded and the token exists:

```bash
python scripts/maintenance/bootstrap_home_assistant_inventory.py
```

Useful variants:

```bash
python scripts/maintenance/bootstrap_home_assistant_inventory.py --format env
python scripts/maintenance/bootstrap_home_assistant_inventory.py --format json --output tmp/home_inventory.json
```

The script will:

- show the entities Mia can currently see
- group them by area
- suggest `MIA_HOME_ENTITY_ALIASES_JSON`

## Readiness check

Use this when you want one quick report for containers, local ports, token presence, and workflow sync:

```bash
python scripts/maintenance/check_smarthome_readiness.py
```

This is especially useful right after editing `.env` or after re-importing workflows.

## One-command apply

After changing `.env`, aliases, or smart-home workflows, you can run:

```bash
python scripts/maintenance/apply_smarthome_changes.py
```

Useful variants:

```bash
python scripts/maintenance/apply_smarthome_changes.py --skip-sync
python scripts/maintenance/apply_smarthome_changes.py --readiness-only
```

This helper will:

- validate workflow JSON
- validate tool contracts
- sync the smart-home workflows to n8n
- restart the relevant containers
- print the final readiness report

## Restart commands

Use the root `.env` explicitly:

```bash
docker compose --env-file /home/huynhminh/Projects/mia-agent/.env -f /home/huynhminh/Projects/mia-agent/infra/docker-compose.yml up -d --build --no-deps n8n mia-core home-assistant memory-embedder
```

## Device-specific notes for the current setup

### Tuya IR remote

- Best used through Home Assistant as the real bridge.
- Fan and air-conditioner may appear as helper entities, scripts, or climate/fan wrappers depending on the integration path.
- Name those wrappers clearly before exposing them to Mia.
- If Home Assistant marks the raw IR devices as `unsupported`, create named Home Assistant scripts such as `Bật quạt phòng ngủ`, `Tắt quạt phòng ngủ`, `Bật máy lạnh phòng ngủ`, `Tắt máy lạnh phòng ngủ`, then add `mia_allowed` to those script entities.

### Tuya lights and switches

- Put each one in the correct Area.
- Add `mia_allowed` only to the final control entity, not every diagnostic entity.

### Xiaomi air purifier

- Prefer the main purifier entity only.
- If the integration creates sensors, keep them unlabeled unless Mia truly needs them.

### Google Home speaker

- Keep Google Home as-is for daily use.
- In Home Assistant, expose the Cast/media player entity for volume, play/pause, and TTS.

## Starter package template

There is a sample package at:

- `infra/homeassistant/config/packages/mia_starter_package.example.yaml`

Use it only as a reference. Replace example entity IDs with real ones from your Home Assistant inventory before enabling any part of it.

## Safe expansion rules

- Add Areas before aliases.
- Add labels before testing Mia commands.
- Expose only control entities, not noisy sensors by default.
- If two devices could answer to the same nickname, add explicit aliases in `MIA_HOME_ENTITY_ALIASES_JSON`.

## Good first test phrases

- `phòng ngủ đang bật gì`
- `bật đèn phòng ngủ`
- `tắt công tắc pc`
- `giảm đèn phòng ngủ xuống 40%`
- `chỉnh máy lạnh phòng ngủ 26 độ`
- `bật máy lọc không khí phòng ngủ`
- `loa phòng ngủ đọc: đến giờ đi ngủ`
