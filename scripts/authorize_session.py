#!/usr/bin/env python3
"""Interactive Telegram session authorization script.

This script helps to authorize a new Telegram session by:
1. Reading credentials from .env
2. Connecting to Telegram API
3. Requesting and entering verification code
4. Saving authorized session file

Run this before first use of the fetcher service.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from src.core.config import FetcherConfig
from src.observability.logging_config import setup_logging, get_logger


async def authorize_session():
    """Interactively authorize Telegram session."""
    
    # Load configuration
    try:
        config = FetcherConfig()
        config.validate_mode_requirements()
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        print("\nMake sure .env file exists and contains:")
        print("  - TELEGRAM_API_ID")
        print("  - TELEGRAM_API_HASH")
        print("  - TELEGRAM_PHONE")
        return 1
    
    # Setup logging
    setup_logging(
        level="INFO",
        log_format="text",
        service_name="authorize-session",
        loki_url=None  # No Loki for interactive script
    )
    logger = get_logger(__name__)
    
    # Create session file path
    session_file = config.get_session_file(config.telegram_phone)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("🔐 Telegram Session Authorization")
    print("=" * 60)
    print(f"\nPhone: {config.telegram_phone}")
    print(f"Session file: {session_file}")
    print()
    
    # Create Telegram client
    client = TelegramClient(
        str(session_file),
        config.telegram_api_id,
        config.telegram_api_hash
    )
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            print("✅ Session already authorized!")
            me = await client.get_me()
            print(f"\nAuthorized as: {me.first_name} {me.last_name or ''}")
            print(f"Username: @{me.username or 'N/A'}")
            print(f"Phone: {me.phone}")
            return 0
        
        print("📱 Sending verification code to your Telegram...")
        await client.send_code_request(config.telegram_phone)
        
        print("\n⏳ Check your Telegram app for the verification code")
        code = input("Enter the code: ").strip()
        
        try:
            await client.sign_in(config.telegram_phone, code)
        except SessionPasswordNeededError:
            print("\n🔒 Two-factor authentication enabled")
            password = input("Enter your 2FA password: ").strip()
            await client.sign_in(password=password)
        
        # Verify authorization
        if await client.is_user_authorized():
            me = await client.get_me()
            print("\n✅ Authorization successful!")
            print(f"\nAuthorized as: {me.first_name} {me.last_name or ''}")
            print(f"Username: @{me.username or 'N/A'}")
            print(f"Phone: {me.phone}")
            print(f"\n💾 Session saved to: {session_file}")
            print("\n🚀 You can now run the fetcher service!")
            logger.info(
                "Session authorized successfully",
                extra={
                    "phone": config.telegram_phone,
                    "user_id": me.id,
                    "username": me.username
                }
            )
            return 0
        else:
            print("\n❌ Authorization failed. Please try again.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Authorization cancelled by user")
        return 1
    except Exception as e:
        logger.exception("Authorization error")
        print(f"\n❌ Error: {e}")
        return 1
    finally:
        await client.disconnect()


def main():
    """Main entry point."""
    print("\n")
    exit_code = asyncio.run(authorize_session())
    print("\n")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
