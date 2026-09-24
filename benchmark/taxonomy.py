"""Capability taxonomy shared with the `indonesia-auto-benchmark` research skill.

Kept in sync by hand with:
  indonesia-automotive-digital-benchmark (1)/skills/indonesia-auto-benchmark/references/capability-taxonomy.md

This is not a hard whitelist. The research skill is explicitly allowed to
discover new capabilities ("Add new capabilities when genuinely new
functionality is discovered"), so `validate()` only warns on unknown
category/capability pairs instead of rejecting them.
"""

from __future__ import annotations

TAXONOMY: dict[str, list[str]] = {
    "DISCOVER": [
        "Vehicle catalogue", "Model search", "Body-style filters",
        "Powertrain filters", "Price filters", "Lifestyle filters",
        "Model finder", "Product recommendation", "Vehicle comparison",
        "Educational content", "EV education", "Hybrid education",
        "Search functionality", "Personalised discovery",
    ],
    "EXPLORE": [
        "Rich model pages", "Interactive galleries", "360-degree exterior",
        "360-degree interior", "Interior exploration", "Interactive hotspots",
        "Colour visualisation", "Trim visualisation", "Wheel visualisation",
        "Specification comparison", "Technology explainers",
        "Interactive technology demos", "Video", "AR", "VR",
        "Virtual showroom",
    ],
    "CONFIGURE": [
        "Model configurator", "Variant selection", "Exterior colour selection",
        "Interior selection", "Wheels", "Accessories", "Packages",
        "Dynamic pricing", "Configuration summary", "Save configuration",
        "Share configuration", "Configuration ID/code",
        "Configuration to dealer", "Configuration to finance",
        "Configuration to inventory",
    ],
    "PRICE & FINANCE": [
        "Public pricing", "Location-based pricing", "Dealer-specific pricing",
        "Promotion visibility", "Discount visibility", "Finance calculator",
        "Monthly instalment calculator", "Down-payment calculator",
        "Loan tenure selection", "Interest-rate information",
        "Insurance integration", "Cost-of-ownership calculator", "Leasing",
        "Finance application", "Finance pre-qualification",
    ],
    "CONVERT": [
        "Request quote", "Test-drive booking", "Callback", "Contact form",
        "WhatsApp", "Live sales consultation", "Dealer selection",
        "Salesperson contact", "Lead routing", "Online reservation",
        "Reservation payment", "Online ordering", "End-to-end digital purchase",
    ],
    "DEALER & INVENTORY": [
        "Dealer locator", "Geolocation", "Map dealer search",
        "Dealer filtering", "Distance calculation", "Opening hours",
        "Dealer service information", "Direct dealer contact",
        "Dealer appointment", "Inventory search", "Available-now vehicles",
        "Dealer-level stock", "VIN-level stock", "Delivery estimate",
        "Vehicle availability", "Inventory linked to configuration",
    ],
    "TRADE-IN & USED VEHICLES": [
        "Trade-in information", "Trade-in valuation", "Automated valuation",
        "Dealer trade-in request", "Used vehicle catalogue",
        "Certified used programme", "Used vehicle search",
        "Used vehicle finance", "Used vehicle reservation",
        "Used vehicle ecommerce",
    ],
    "OWNERSHIP & AFTERSALES": [
        "Service booking", "Service appointment selection",
        "Dealer service selection", "Maintenance schedule",
        "Maintenance pricing", "Service cost estimator", "Service packages",
        "Warranty", "Warranty checker", "Roadside assistance",
        "Parts catalogue", "Parts search", "Accessories",
        "Accessory ecommerce", "Owner manuals", "Recall checker",
        "Vehicle history", "Customer account", "Service history",
    ],
    "CONNECTED VEHICLE": [
        "Mobile application", "Vehicle status", "Vehicle location",
        "Remote lock/unlock", "Remote engine start", "Remote climate control",
        "Vehicle diagnostics", "Maintenance alerts", "Driving data",
        "Trip history", "Geofencing", "Security alerts", "Digital key",
        "OTA updates", "Charging control", "Connected navigation",
    ],
    "ELECTRIFICATION": [
        "EV education", "Battery information", "Battery warranty",
        "Range information", "Range calculator", "Charging-time calculator",
        "Charging map", "Public charging information",
        "Charging-station availability", "Home charging",
        "Home-charger purchase", "Charging partnerships", "Charging payment",
        "Energy-cost calculator", "EV vs ICE comparison",
        "Environmental-impact calculator",
    ],
    "CUSTOMER ASSISTANCE": [
        "FAQ", "Website search", "Live chat", "Chatbot", "WhatsApp chatbot",
        "Virtual sales assistant", "Natural-language search", "AI assistant",
        "Product recommendation assistant", "Service assistant",
        "Voice assistant",
    ],
    "PERSONALISATION & RETENTION": [
        "User login", "Customer profile", "Vehicle profile", "Saved vehicle",
        "Saved comparison", "Saved configuration", "Saved dealer",
        "Recently viewed vehicles", "Personalised recommendations",
        "Personalised offers", "Owner content", "Loyalty programme",
        "CRM continuity",
    ],
    "OMNICHANNEL": [
        "Website-to-dealer continuity", "Configuration hand-off",
        "Digital lead visibility at dealer", "Appointment continuity",
        "Customer identity continuity", "Online-to-offline purchase continuation",
        "App-to-website continuity", "Dealer-to-app continuity",
    ],
    "EMERGING EXPERIENCES": [
        "Generative AI", "Augmented reality", "Mixed reality",
        "Virtual showroom", "Video consultation", "Remote sales consultation",
        "Real-time inventory", "Dynamic personalisation",
        "Conversational commerce", "Digital identity", "Digital key",
        "Vehicle subscription", "Integrated mobility services",
        "Advanced charging ecosystem", "Ecommerce innovation",
    ],
}

CATEGORY_ORDER = list(TAXONOMY.keys())


def known_capabilities() -> set[tuple[str, str]]:
    return {
        (category, capability)
        for category, capabilities in TAXONOMY.items()
        for capability in capabilities
    }


def is_known(category: str, capability: str) -> bool:
    return (category.strip(), capability.strip()) in known_capabilities()
