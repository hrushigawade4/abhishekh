from datetime import datetime

def get_abhishek_schedule(bhakts, sacred_dates):
    schedule = {}

    for bhakt in bhakts:
        bhakt_id = bhakt[0]
        name = bhakt[1]
        abhishek_type = bhakt[3]
        duration_months = bhakt[4]
        start_date = datetime.strptime(bhakt[5], "%Y-%m-%d")
        end_date = datetime.strptime(bhakt[6], "%Y-%m-%d")

        # Get sacred dates of that type
        all_dates = sacred_dates.get(abhishek_type, [])
        bhakt_dates = []

        for d in all_dates:
            dt = datetime.strptime(d, "%Y-%m-%d")
            if start_date <= dt <= end_date:
                bhakt_dates.append(dt.strftime("%Y-%m-%d"))

        schedule[name] = {
            "abhishek_type": abhishek_type,
            "duration": duration_months,
            "dates": bhakt_dates
        }

    return schedule
