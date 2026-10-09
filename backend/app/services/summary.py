from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP


def number(value):
    return float(value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def summarize(records):
    rows = sorted(records, key=lambda r: r['date'])
    base = {'count': len(rows), 'unit': 'KRW/L', 'product': '보통휘발유',
            'region': '전국', 'as_of': rows[-1]['date'] if rows else None}
    if not rows:
        return {**base, 'period': None, 'metrics': None, 'monthly': [],
                'trend': {'status': '자료 부족'}, 'period_change_pct': None}
    prices = [Decimal(str(r['value'])) for r in rows]
    low, high = min(prices), max(prices)
    groups = defaultdict(list)
    for r, p in zip(rows, prices):
        groups[r['date'][:7]].append(p)
    last = date.fromisoformat(rows[-1]['date'])
    by_date = {date.fromisoformat(r['date']): p for r, p in zip(rows, prices)}
    recent_dates = [last - timedelta(days=i) for i in range(7)]
    prior_dates = [last - timedelta(days=i) for i in range(7, 14)]
    trend = {'status': '자료 부족', 'recent_period': [str(last-timedelta(days=6)), str(last)],
             'previous_period': [str(last-timedelta(days=13)), str(last-timedelta(days=7))]}
    if all(d in by_date for d in recent_dates + prior_dates):
        recent = sum(by_date[d] for d in recent_dates) / 7
        prior = sum(by_date[d] for d in prior_dates) / 7
        diff = recent - prior
        trend.update(status='상승' if diff > 0 else '하락' if diff < 0 else '동일',
                     recent_average=number(recent), previous_average=number(prior),
                     difference=number(diff), change_pct=number(diff / prior * 100))
    return {**base, 'period': [rows[0]['date'], rows[-1]['date']],
            'modified_count': sum(bool(r.get('is_modified')) for r in rows),
            'user_input_count': sum(r.get('source') == 'user' for r in rows),
            'metrics': {'average': number(sum(prices)/len(prices)), 'min': number(low),
                        'max': number(high),
                        'min_dates': [r['date'] for r,p in zip(rows,prices) if p == low],
                        'max_dates': [r['date'] for r,p in zip(rows,prices) if p == high]},
            'monthly': [{'month': m, 'count': len(ps), 'average': number(sum(ps)/len(ps))}
                        for m, ps in sorted(groups.items())],
            'trend': trend, 'period_change_pct': number((prices[-1]-prices[0])/prices[0]*100)}
