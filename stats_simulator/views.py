from django.shortcuts import render


def index(request):
    """
    Main view for the statistical sampling simulator.
    Demonstrates Central Limit Theorem through interactive visualizations.
    """
    context = {
        'page_title': 'Statistical Sampling Simulator',
    }
    return render(request, 'stats_simulator/index.html', context)
