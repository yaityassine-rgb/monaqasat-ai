import { useState, useEffect, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  Users,
  Plus,
  Loader2,
  Crown,
  Shield,
  User,
  Mail,
  Trash2,
  Lock,
  FileText,
  Bookmark,
} from "lucide-react";
import { useAuth } from "../../lib/auth-context";
import { supabase, isSupabaseConfigured } from "../../lib/supabase";
import { useSubscription } from "../../lib/use-subscription";
import { Link } from "react-router-dom";
import { useLang, localizedPath } from "../../lib/use-lang";

interface Team {
  id: string;
  name: string;
  owner_id: string;
  max_members: number;
  created_at: string;
}

interface TeamMember {
  id: number;
  user_id: string;
  role: "owner" | "admin" | "member";
  invited_email: string | null;
  status: string;
  joined_at: string;
}

interface SharedTender {
  id: number;
  tender_id: string;
  notes: string | null;
  created_at: string;
}

interface SharedProposal {
  id: number;
  proposal_id: string;
  created_at: string;
}

const ROLE_ICONS = {
  owner: Crown,
  admin: Shield,
  member: User,
};

export default function TeamPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const { tier } = useSubscription();
  const urlLang = useLang();
  const [team, setTeam] = useState<Team | null>(null);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [sharedTenders, setSharedTenders] = useState<SharedTender[]>([]);
  const [sharedProposals, setSharedProposals] = useState<SharedProposal[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [teamName, setTeamName] = useState("");
  const [inviteEmail, setInviteEmail] = useState("");
  const [tab, setTab] = useState<"members" | "tenders" | "proposals">("members");

  const canUseTeams = tier === "business";

  const fetchTeam = useCallback(async () => {
    if (!user || !isSupabaseConfigured) {
      setLoading(false);
      return;
    }

    // Find team where user is a member
    const { data: membership } = await supabase
      .from("team_members")
      .select("team_id")
      .eq("user_id", user.id)
      .eq("status", "active")
      .limit(1)
      .single();

    if (membership) {
      const [{ data: teamData }, { data: membersData }, { data: tendersData }, { data: proposalsData }] =
        await Promise.all([
          supabase.from("teams").select("*").eq("id", membership.team_id).single(),
          supabase.from("team_members").select("*").eq("team_id", membership.team_id).order("joined_at"),
          supabase.from("team_shared_tenders").select("*").eq("team_id", membership.team_id).order("created_at", { ascending: false }).limit(20),
          supabase.from("team_shared_proposals").select("*").eq("team_id", membership.team_id).order("created_at", { ascending: false }).limit(20),
        ]);

      setTeam(teamData);
      setMembers(membersData || []);
      setSharedTenders(tendersData || []);
      setSharedProposals(proposalsData || []);
    }

    setLoading(false);
  }, [user]);

  useEffect(() => {
    fetchTeam();
  }, [fetchTeam]);

  const createTeam = async () => {
    if (!user || !teamName.trim()) return;
    setCreating(true);

    try {
      const { data: newTeam, error: teamError } = await supabase
        .from("teams")
        .insert({ name: teamName.trim(), owner_id: user.id })
        .select("id")
        .single();

      if (teamError) throw teamError;

      // Add creator as owner
      await supabase.from("team_members").insert({
        team_id: newTeam!.id,
        user_id: user.id,
        role: "owner",
        status: "active",
      });

      await fetchTeam();
      setTeamName("");
    } catch (err) {
      console.error("Create team error:", err);
    }
    setCreating(false);
  };

  const inviteMember = async () => {
    if (!team || !inviteEmail.trim()) return;

    try {
      // Look up user by email
      const { data: { users } } = await supabase.auth.admin.listUsers();
      const invitedUser = users?.find((u) => u.email === inviteEmail.trim());

      if (invitedUser) {
        await supabase.from("team_members").insert({
          team_id: team.id,
          user_id: invitedUser.id,
          role: "member",
          invited_email: inviteEmail.trim(),
          status: "active",
        });
      } else {
        // Store as invited (pending)
        await supabase.from("team_members").insert({
          team_id: team.id,
          user_id: user!.id, // placeholder
          role: "member",
          invited_email: inviteEmail.trim(),
          status: "invited",
        });
      }

      await fetchTeam();
      setInviteEmail("");
    } catch (err) {
      console.error("Invite error:", err);
    }
  };

  const removeMember = async (memberId: number) => {
    await supabase.from("team_members").update({ status: "removed" }).eq("id", memberId);
    setMembers((prev) => prev.filter((m) => m.id !== memberId));
  };

  // Tier gate
  if (!canUseTeams) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md"
        >
          <Lock className="w-16 h-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-white mb-2">
            {t("team.upgradeRequired")}
          </h2>
          <p className="text-slate-400 text-sm mb-6">{t("team.upgradeDesc")}</p>
          <Link
            to={localizedPath(urlLang, "/pricing")}
            className="inline-flex items-center gap-2 px-6 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors"
          >
            {t("team.upgradeCta")}
          </Link>
        </motion.div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 text-primary animate-spin" />
      </div>
    );
  }

  // No team yet — create one
  if (!team) {
    return (
      <div className="mx-auto max-w-lg px-4 py-12 sm:px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card rounded-2xl p-8 text-center"
        >
          <Users className="w-14 h-14 text-primary-light mx-auto mb-4" />
          <h1 className="text-xl font-bold text-white mb-2">{t("team.createTitle")}</h1>
          <p className="text-slate-400 text-sm mb-6">{t("team.createDesc")}</p>

          <input
            type="text"
            value={teamName}
            onChange={(e) => setTeamName(e.target.value)}
            placeholder={t("team.teamNamePh")}
            className="w-full bg-dark/60 border border-dark-border rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-primary/50 mb-4"
          />

          <button
            onClick={createTeam}
            disabled={creating || !teamName.trim()}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-primary hover:bg-primary-dark text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-50"
          >
            {creating ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            {t("team.create")}
          </button>
        </motion.div>
      </div>
    );
  }

  // Team workspace
  const isOwnerOrAdmin = members.some(
    (m) => m.user_id === user?.id && (m.role === "owner" || m.role === "admin")
  );

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Users className="w-6 h-6 text-primary-light" />
              {team.name}
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              {members.filter((m) => m.status === "active").length}/{team.max_members}{" "}
              {t("team.members")}
            </p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 border-b border-dark-border">
          {(["members", "tenders", "proposals"] as const).map((key) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                tab === key
                  ? "border-primary text-white"
                  : "border-transparent text-slate-400 hover:text-white"
              }`}
            >
              {t(`team.tab.${key}`)}
            </button>
          ))}
        </div>

        {/* Members tab */}
        {tab === "members" && (
          <div className="space-y-4">
            {/* Invite */}
            {isOwnerOrAdmin && members.filter((m) => m.status === "active").length < team.max_members && (
              <div className="glass-card rounded-xl p-4 flex items-center gap-3">
                <Mail className="w-4 h-4 text-slate-400 shrink-0" />
                <input
                  type="email"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder={t("team.invitePh")}
                  className="flex-1 bg-transparent text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none"
                />
                <button
                  onClick={inviteMember}
                  disabled={!inviteEmail.trim()}
                  className="px-3 py-1.5 bg-primary text-white text-xs font-medium rounded-lg hover:bg-primary-dark transition-colors disabled:opacity-50"
                >
                  {t("team.invite")}
                </button>
              </div>
            )}

            {/* Member list */}
            {members
              .filter((m) => m.status !== "removed")
              .map((member) => {
                const RoleIcon = ROLE_ICONS[member.role];
                return (
                  <div
                    key={member.id}
                    className="glass-card rounded-xl p-4 flex items-center gap-3"
                  >
                    <div className="w-9 h-9 rounded-full bg-primary/10 flex items-center justify-center">
                      <RoleIcon className="w-4 h-4 text-primary-light" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">
                        {member.invited_email || member.user_id.slice(0, 8)}
                      </p>
                      <p className="text-xs text-slate-500 capitalize">
                        {member.role}
                        {member.status === "invited" && ` · ${t("team.pending")}`}
                      </p>
                    </div>
                    {isOwnerOrAdmin && member.role !== "owner" && (
                      <button
                        onClick={() => removeMember(member.id)}
                        className="p-1.5 text-slate-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                );
              })}
          </div>
        )}

        {/* Shared tenders tab */}
        {tab === "tenders" && (
          <div className="space-y-3">
            {sharedTenders.length === 0 ? (
              <div className="text-center py-12">
                <Bookmark className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-sm text-slate-400">{t("team.noSharedTenders")}</p>
              </div>
            ) : (
              sharedTenders.map((st) => (
                <Link
                  key={st.id}
                  to={localizedPath(urlLang, `/dashboard/tender/${st.tender_id}`)}
                  className="block glass-card rounded-xl p-4 hover:bg-white/[0.02] transition-colors"
                >
                  <p className="text-sm font-medium text-white">{st.tender_id}</p>
                  {st.notes && (
                    <p className="text-xs text-slate-400 mt-1">{st.notes}</p>
                  )}
                  <p className="text-[10px] text-slate-500 mt-1">
                    {new Date(st.created_at).toLocaleDateString()}
                  </p>
                </Link>
              ))
            )}
          </div>
        )}

        {/* Shared proposals tab */}
        {tab === "proposals" && (
          <div className="space-y-3">
            {sharedProposals.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
                <p className="text-sm text-slate-400">{t("team.noSharedProposals")}</p>
              </div>
            ) : (
              sharedProposals.map((sp) => (
                <Link
                  key={sp.id}
                  to={localizedPath(urlLang, `/dashboard/proposals/${sp.proposal_id}`)}
                  className="block glass-card rounded-xl p-4 hover:bg-white/[0.02] transition-colors"
                >
                  <p className="text-sm font-medium text-white">{sp.proposal_id}</p>
                  <p className="text-[10px] text-slate-500 mt-1">
                    {new Date(sp.created_at).toLocaleDateString()}
                  </p>
                </Link>
              ))
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
}
