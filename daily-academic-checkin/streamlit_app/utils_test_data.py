from datetime import datetime, timedelta
from typing import List, Dict, Any


def sample_logs(n: int = 15) -> List[Dict[str, Any]]:
	rows = []
	for i in range(n):
		rows.append({
			"id": f"log_{i}",
			"date": (datetime.utcnow() - timedelta(days=i)).date().isoformat(),
			"subject": "Math" if i % 2 == 0 else "Science",
			"topics": ["Algebra", "Calculus"] if i % 2 == 0 else ["Physics"],
			"notes": "Found it hard" if i % 5 == 0 else "",
		})
	return rows