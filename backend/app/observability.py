from collections import Counter
from time import monotonic

class Metrics:
    def __init__(self):
        self.jobs=Counter(); self.agent_calls=Counter(); self.failures=Counter(); self.total_processing_seconds=0.0; self.started={}
    def job_started(self,job_id): self.jobs['started']+=1; self.started[job_id]=monotonic()
    def job_finished(self,job_id,status):
        self.jobs[status.lower()]+=1
        if job_id in self.started: self.total_processing_seconds += monotonic()-self.started.pop(job_id)
        if status=='FAILED': self.failures['processing']+=1
    def agent(self,agent_id): self.agent_calls[agent_id]+=1
    def prometheus(self):
        lines=['# HELP thatsawrap_jobs_total Processing jobs by state','# TYPE thatsawrap_jobs_total counter']
        for key,val in self.jobs.items(): lines.append(f'thatsawrap_jobs_total{{state="{key}"}} {val}')
        lines += ['# HELP thatsawrap_agent_calls_total Agent executions','# TYPE thatsawrap_agent_calls_total counter']
        for key,val in self.agent_calls.items(): lines.append(f'thatsawrap_agent_calls_total{{agent="{key}"}} {val}')
        lines += ['# HELP thatsawrap_failures_total Processing failures','# TYPE thatsawrap_failures_total counter']
        for key,val in self.failures.items(): lines.append(f'thatsawrap_failures_total{{type="{key}"}} {val}')
        lines.append(f'thatsawrap_processing_seconds_total {self.total_processing_seconds:.3f}')
        return '\n'.join(lines)+'\n'
