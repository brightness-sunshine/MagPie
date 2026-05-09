import json

payload = {
    'text': (
        "**You’ve already got a way of organizing what matters.**\n\n"
        "I can follow the trails you’ve already made, or build you a clever new map. 🪶"
    ),
    'buttons': [
        [
            {'text': 'Use my folders', 'callback_data': 'magpie:first_run:folders', 'style': 'primary'},
            {'text': 'Organize intelligently', 'callback_data': 'magpie:first_run:smart'},
        ],
        [
            {'text': 'Show me both', 'callback_data': 'magpie:first_run:both'}
        ]
    ]
}

print(json.dumps(payload, indent=2))
