#!/usr/bin/env python
"""Quick test script to verify Finnhub setup is working.

Run this after setting your FINNHUB_API_KEY environment variable:
    export FINNHUB_API_KEY="your_key_here"
    python test_finnhub_setup.py
"""
import sys

try:
    from option_research import FinnhubClient
    
    print("✓ Successfully imported FinnhubClient")
    print("\nAttempting to initialize Finnhub client...")
    
    try:
        client = FinnhubClient()
        print("✓ Client initialized successfully")
        
        print("\nFetching upcoming earnings (next 3 days)...")
        events = client.get_upcoming_earnings(days_ahead=3)
        
        print(f"✓ Successfully fetched {len(events)} earnings events")
        
        if events:
            print("\nSample events:")
            for event in events[:5]:
                print(f"  - {event.ticker}: {event.earnings_date} (expiry: {event.event_expiry})")
        else:
            print("\n(No earnings in the next 3 days - this is normal)")
        
        print("\n" + "="*60)
        print("✓ FINNHUB SETUP COMPLETE!")
        print("="*60)
        print("\nYou can now:")
        print("1. Run the example: python examples/fetch_earnings.py")
        print("2. Use FinnhubClient in your code")
        print("3. Integrate with the options pipeline")
        
    except ValueError as e:
        print(f"\n✗ Error: {e}")
        print("\nTo fix this:")
        print("1. Get a free API key at: https://finnhub.io/register")
        print("2. Set environment variable:")
        print("   export FINNHUB_API_KEY='your_key_here'")
        print("3. Or create a .env file with:")
        print("   FINNHUB_API_KEY=your_key_here")
        sys.exit(1)
        
    except RuntimeError as e:
        print(f"\n✗ API Error: {e}")
        print("\nPossible causes:")
        print("- Invalid API key")
        print("- Network connection issue")
        print("- Rate limit exceeded (wait 1 minute and retry)")
        sys.exit(1)

except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nPlease run: pip install -e .")
    sys.exit(1)

