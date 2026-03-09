-- ============================================================
-- Team Features — teams, members, shared resources
-- ============================================================

CREATE TABLE teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  max_members INTEGER NOT NULL DEFAULT 5,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE team_members (
  id BIGSERIAL PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
  invited_email TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'invited', 'removed')),
  joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(team_id, user_id)
);

CREATE TABLE team_shared_tenders (
  id BIGSERIAL PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  tender_id TEXT NOT NULL REFERENCES tenders(id) ON DELETE CASCADE,
  shared_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(team_id, tender_id)
);

CREATE TABLE team_shared_proposals (
  id BIGSERIAL PRIMARY KEY,
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  proposal_id UUID NOT NULL REFERENCES proposals(id) ON DELETE CASCADE,
  shared_by UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(team_id, proposal_id)
);

-- Indexes
CREATE INDEX idx_teams_owner ON teams(owner_id);
CREATE INDEX idx_team_members_user ON team_members(user_id);
CREATE INDEX idx_team_members_team ON team_members(team_id);
CREATE INDEX idx_team_shared_tenders_team ON team_shared_tenders(team_id);
CREATE INDEX idx_team_shared_proposals_team ON team_shared_proposals(team_id);

-- Triggers
CREATE TRIGGER trg_teams_updated
  BEFORE UPDATE ON teams
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- RLS
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_shared_tenders ENABLE ROW LEVEL SECURITY;
ALTER TABLE team_shared_proposals ENABLE ROW LEVEL SECURITY;

-- Teams: members can view their teams
CREATE POLICY "Team members can view team"
  ON teams FOR SELECT TO authenticated
  USING (id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND status = 'active'));

CREATE POLICY "Users can create teams"
  ON teams FOR INSERT TO authenticated
  WITH CHECK (owner_id = auth.uid());

CREATE POLICY "Team owners can update team"
  ON teams FOR UPDATE TO authenticated
  USING (owner_id = auth.uid());

CREATE POLICY "Team owners can delete team"
  ON teams FOR DELETE TO authenticated
  USING (owner_id = auth.uid());

-- Team members: members see their team's members
CREATE POLICY "Team members can view members"
  ON team_members FOR SELECT TO authenticated
  USING (team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND status = 'active'));

CREATE POLICY "Team admins can manage members"
  ON team_members FOR INSERT TO authenticated
  WITH CHECK (team_id IN (
    SELECT team_id FROM team_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin') AND status = 'active'
  ));

CREATE POLICY "Team admins can update members"
  ON team_members FOR UPDATE TO authenticated
  USING (team_id IN (
    SELECT team_id FROM team_members WHERE user_id = auth.uid() AND role IN ('owner', 'admin') AND status = 'active'
  ));

-- Shared tenders: team members can view/share
CREATE POLICY "Team members can view shared tenders"
  ON team_shared_tenders FOR SELECT TO authenticated
  USING (team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND status = 'active'));

CREATE POLICY "Team members can share tenders"
  ON team_shared_tenders FOR INSERT TO authenticated
  WITH CHECK (team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND status = 'active'));

-- Shared proposals: team members can view/share
CREATE POLICY "Team members can view shared proposals"
  ON team_shared_proposals FOR SELECT TO authenticated
  USING (team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND status = 'active'));

CREATE POLICY "Team members can share proposals"
  ON team_shared_proposals FOR INSERT TO authenticated
  WITH CHECK (team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid() AND status = 'active'));
