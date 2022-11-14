"""Command used in order to check if a new hero is in the heroes list, compared
to the internal heroes list. If this is a case, a Discord notification is sent to the
developer.
"""
from overfastapi.common.helpers import overfast_request, send_discord_webhook_message
from overfastapi.common.logging import logger
from overfastapi.config import DISCORD_WEBHOOK_ENABLED


def main():
    """Main method of the script"""
    logger.info("Checking if Blizzard career pages are back...")
    if not DISCORD_WEBHOOK_ENABLED:
        logger.info("No Discord webhook configured ! Exiting...")
        raise SystemExit

    logger.info("OK ! Starting to check if the Blizzard career pages are back...")

    career_page_url = "https://overwatch.blizzard.com/en-us/career/pc/TeKrop-2217/"
    req = overfast_request(career_page_url)
    if req.status_code != 200:
        error_message = (
            f"Received an error from Blizzard. HTTP {req.status_code} : {req.text}",
        )
        logger.error(error_message)
        send_discord_webhook_message(error_message)
        raise SystemExit

    if "Profiles Under Maintenance" in req.text:
        logger.info("Profiles are still under maintenance...")
        raise SystemExit

    send_discord_webhook_message("Blizzard career pages are back 🥳")


if __name__ == "__main__":
    logger = logger.patch(lambda record: record.update(name="check_career_pages"))
    main()
