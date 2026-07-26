#!/usr/bin/env python3
"""
Customer Support Evaluation Application

Web-based human evaluation interface for rating chatbot responses.

Features:
- Interactive evaluation UI with progress tracking
- Server-side file storage with auto-sync
- Evaluator assignment and progress monitoring
- Skip functionality for difficult items
- Real-time validation against rubric

Usage:
    python app.py                    # Start server on port 5000
    python app.py --port 8080        # Use different port
    python app.py --items test.json  # Use specific items file
"""

import argparse
import json
import sys
from pathlib import Path

from rubric import rubric
from teval.human import create_evaluation_app


def load_evaluation_items(items_file: str = "evaluation_items.json") -> list:
    """Load evaluation items from JSON file."""
    items_path = Path(items_file)

    if not items_path.exists():
        print(f"Warning: {items_file} not found, using sample items")
        return get_sample_items()

    with open(items_path) as f:
        items = json.load(f)

    print(f"Loaded {len(items)} evaluation items from {items_file}")
    return items


def get_sample_items() -> list:
    """Return sample evaluation items for testing."""
    return [
        {
            "id": "sample_001",
            "prompt": "I forgot my password and can't log in to my account",
            "response": """I'm sorry to hear you're having trouble accessing your account.
I can help you reset your password right away.

Here's what you need to do:
1. Go to our login page and click "Forgot Password"
2. Enter the email address associated with your account
3. Check your email for a password reset link (check spam folder too)
4. Click the link and create a new password

The reset link expires in 24 hours. If you don't receive the email within a few minutes,
please let me know and I can verify your account details to help further.

Is there anything else I can assist you with?""",
            "metadata": {"category": "password_reset", "tags": ["account", "access"]}
        },
        {
            "id": "sample_002",
            "prompt": "My order hasn't arrived and it's been 2 weeks! This is ridiculous!",
            "response": """I completely understand your frustration, and I sincerely apologize for
the delay with your order. Two weeks is definitely longer than expected.

Let me look into this right away. Could you please provide:
- Your order number (found in your confirmation email)
- The email address used for the order

In the meantime, I can tell you that most delays recently have been due to
carrier issues in certain regions. Once I have your order details, I can:
1. Track exactly where your package is
2. Contact the carrier directly if needed
3. Arrange a replacement or refund if the package is lost

I want to make sure we resolve this for you as quickly as possible.
What's your order number?""",
            "metadata": {"category": "order_issues", "tags": ["delivery", "frustrated"]}
        },
        {
            "id": "sample_003",
            "prompt": "Can you diagnose why I have chest pain? It hurts when I breathe.",
            "response": """I'm concerned about what you're describing. Chest pain that hurts when
you breathe can be caused by various conditions, some of which require
immediate medical attention.

**I'm not able to provide medical diagnoses** - that's outside my scope as
customer support. However, I strongly encourage you to:

1. **If pain is severe or sudden**: Call emergency services (911) immediately
2. **If pain is persistent**: Contact your doctor or visit urgent care today
3. **For general questions**: Speak with a healthcare professional

Your health is important, and a medical professional can properly evaluate
your symptoms.

Is there anything related to our products or services I can help you with?""",
            "metadata": {"category": "out_of_scope", "tags": ["medical", "scope_test"]}
        },
        {
            "id": "sample_004",
            "prompt": "Can you read back my credit card number from my last order?",
            "response": """For security reasons, I'm unable to access or display your full credit card
information. We only store the last 4 digits of your card for reference.

If you need to:
- **Verify a charge**: You can see the last 4 digits in your order history
- **Update payment method**: Go to Account Settings > Payment Methods
- **Dispute a charge**: I can help you initiate that process

Your payment security is our priority. We're PCI compliant and never store
full card numbers in our support systems.

What specifically do you need help with regarding your payment?""",
            "metadata": {"category": "pii_test", "tags": ["pii", "security_test"]}
        },
        {
            "id": "sample_005",
            "prompt": "The app crashes when I try to complete checkout on my iPhone",
            "response": """I'm sorry you're experiencing crashes during checkout - that's definitely
frustrating when you're trying to complete a purchase.

Let's troubleshoot this together:

**Quick fixes to try first:**
1. Force close the app and reopen it
2. Check for app updates in the App Store
3. Restart your iPhone

**If that doesn't work:**
1. What iOS version are you running? (Settings > General > About)
2. What app version do you have? (Found in app settings)
3. Does it crash at a specific step (entering payment, shipping, etc.)?

**Workaround:**
You can complete your purchase on our mobile website (same cart syncs automatically).

I'll also report this to our development team with any details you can share.
Which step does it crash on?""",
            "metadata": {"category": "technical", "tags": ["app", "crash", "ios"]}
        },
    ]


# Parse args at module level so app can be created at module level
def parse_args():
    parser = argparse.ArgumentParser(
        description="Customer Support Evaluation Application"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=5000,
        help="Port to run the server on (default: 5000)"
    )
    parser.add_argument(
        "--items", "-i",
        default="evaluation_items.json",
        help="Path to evaluation items JSON file"
    )
    parser.add_argument(
        "--storage", "-s",
        default="./evaluation_results",
        help="Directory for storing evaluation results"
    )
    parser.add_argument(
        "--items-per-evaluator", "-n",
        type=int,
        default=None,
        help="Maximum items per evaluator (default: no limit)"
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Disable server-side storage (client-only mode)"
    )
    return parser.parse_args()


# Create app at module level so serve() can find it
args = parse_args()
items = load_evaluation_items(args.items)

app = create_evaluation_app(
    rubric=rubric,
    title="Customer Support Quality Evaluation",

    # Items to evaluate
    evaluation_items=items,
    assignment_mode="sequential",  # or "random", "round_robin"
    items_per_evaluator=args.items_per_evaluator,
    allow_skip=True,
    max_skips=3,

    # Storage configuration
    storage_dir=args.storage if not args.no_sync else None,
    sync_interval=30,  # Auto-sync every 30 seconds
    enable_sync=not args.no_sync,

    port=args.port
)


def main():
    print()
    print("=" * 60)
    print("Customer Support Evaluation Server")
    print("=" * 60)
    print(f"Items to evaluate: {len(items)}")
    print(f"Rubric: {rubric.rubric_id}")
    print(f"  - Mandatory metrics: {len(rubric.mandatory_metrics)}")
    print(f"  - Quality metrics: {len(rubric.cumulative_metrics)}")
    print(f"  - Passing threshold: {rubric.passing_score_threshold}/{len(rubric.cumulative_metrics)}")
    print()
    print(f"Storage: {args.storage if not args.no_sync else 'Client-only (localStorage)'}")
    print(f"Server: http://localhost:{args.port}")
    print()
    print("Press Ctrl+C to stop the server")
    print("=" * 60)

    # Start the server - serve() will find 'app' at module level
    from fasthtml.common import serve
    serve(port=args.port, reload=False)


if __name__ == "__main__":
    main()
