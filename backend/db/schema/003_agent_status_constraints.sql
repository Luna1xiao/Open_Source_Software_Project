CREATE TRIGGER IF NOT EXISTS trg_agent_runs_status_insert
BEFORE INSERT ON agent_runs
WHEN NEW.status NOT IN ('idle', 'queued', 'running', 'success', 'failure', 'cancelled')
BEGIN
  SELECT RAISE(ABORT, 'invalid agent_runs.status');
END;

CREATE TRIGGER IF NOT EXISTS trg_agent_runs_status_update
BEFORE UPDATE OF status ON agent_runs
WHEN NEW.status NOT IN ('idle', 'queued', 'running', 'success', 'failure', 'cancelled')
BEGIN
  SELECT RAISE(ABORT, 'invalid agent_runs.status');
END;
