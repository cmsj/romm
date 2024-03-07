import emoji
import socketio  # type: ignore
from endpoints.platform import PlatformSchema
from endpoints.rom import RomSchema
from exceptions.fs_exceptions import (
    FolderStructureNotMatchException,
    RomsNotFoundException,
)
from handler import (
    db_platform_handler,
    db_rom_handler,
    fs_platform_handler,
    fs_rom_handler,
    socket_handler,
)
from handler.redis_handler import high_prio_queue, redis_url
from handler.scan_handler import (
    scan_platform,
    scan_rom,
    ScanType,
)
from logger.logger import log


def _get_socket_manager():
    # Connect to external socketio server
    return socketio.AsyncRedisManager(redis_url, write_only=True)


async def scan_platforms(
    platform_ids: list[int],
    scan_type: ScanType = "quick",
    selected_roms: list[str] = (),
):
    """Scan all the listed platforms and fetch metadata from different sources

    Args:
        platform_slugs (list[str]): List of platform slugs to be scanned
        scan_type (str): Type of scan to be performed. Defaults to "quick".
        selected_roms (list[str], optional): List of selected roms to be scanned. Defaults to ().
    """

    sm = _get_socket_manager()

    try:
        fs_platforms: list[str] = fs_platform_handler.get_platforms()
    except FolderStructureNotMatchException as e:
        log.error(e)
        await sm.emit("scan:done_ko", e.message)
        return
    
    try:

        platform_list = [
            db_platform_handler.get_platforms(s).fs_slug for s in platform_ids
        ] or fs_platforms

        if len(platform_list) == 0:
            log.warn(
                "⚠️ No platforms found, verify that the folder structure is right and the volume is mounted correctly "
            )
        else:
            log.info(f"Found {len(platform_list)} platforms in file system ")

        for platform_slug in platform_list:
            platform = db_platform_handler.get_platform_by_fs_slug(platform_slug)
            if platform and scan_type == "new_platforms":
                continue

            scanned_platform = scan_platform(platform_slug, fs_platforms)
            if platform:
                scanned_platform.id = platform.id

            platform = db_platform_handler.add_platform(scanned_platform)

            await sm.emit(
                "scan:scanning_platform",
                PlatformSchema.model_validate(platform).model_dump(),
            )

            # Scanning roms
            try:
                fs_roms = fs_rom_handler.get_roms(platform)
            except RomsNotFoundException as e:
                log.error(e)
                continue

            if len(fs_roms) == 0:
                log.warning(
                    "  ⚠️ No roms found, verify that the folder structure is correct"
                )
            else:
                log.info(f"  {len(fs_roms)} roms found")

            for fs_rom in fs_roms:
                rom = db_rom_handler.get_rom_by_filename(platform.id, fs_rom["file_name"])
                should_scan_rom = (
                    (scan_type == "quick" and not rom)
                    or (scan_type == "unidentified" and rom and not rom.igdb_id and not rom.moby_id)
                    or (scan_type == "partial" and rom and (not rom.igdb_id or not rom.moby_id))
                    or (scan_type == "complete")
                    or rom.id in selected_roms
                )

                if should_scan_rom:
                    scanned_rom = await scan_rom(platform, fs_rom, rom, scan_type=scan_type)
                    _added_rom = db_rom_handler.add_rom(scanned_rom)
                    rom = db_rom_handler.get_roms(_added_rom.id)

                    await sm.emit(
                        "scan:scanning_rom",
                        {
                            "platform_name": platform.name,
                            "platform_slug": platform.slug,
                            **RomSchema.model_validate(rom).model_dump(),
                        },
                    )

            db_rom_handler.purge_roms(platform.id, [rom["file_name"] for rom in fs_roms])
        db_platform_handler.purge_platforms(fs_platforms)

        log.info(emoji.emojize(":check_mark:  Scan completed "))
        await sm.emit("scan:done", {})
    except Exception as e:
        log.error(e)
        # Catch all exceptions and emit error to the client
        await sm.emit("scan:done_ko", str(e))


@socket_handler.socket_server.on("scan")
async def scan_handler(_sid: str, options: dict):
    """Scan socket endpoint

    Args:
        options (dict): Socket options
    """

    log.info(emoji.emojize(":magnifying_glass_tilted_right: Scanning "))

    platform_ids = options.get("platforms", [])
    scan_type = options.get("type", False)
    selected_roms = options.get("roms", [])

    # Run in worker if redis is available
    return high_prio_queue.enqueue(
        scan_platforms,
        platform_ids,
        scan_type,
        selected_roms,
        job_timeout=14400,  # Timeout after 4 hours
    )
