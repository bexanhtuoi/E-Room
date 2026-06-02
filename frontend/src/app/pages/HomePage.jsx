import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { fetchJson } from '../../lib/api';
import { useAuth } from '../../app/AuthContext';
import { HeroSection, ProblemSection, PremiumFlowSection, AgentSection, AudienceSection, FinalShowcaseSection, RoomsSection, StatsSection } from '../../components/ui/HomeSections';
import { QueueOverlay } from '../../features/chat/QueueOverlay';
import { MatchFoundCard } from '../../features/chat/MatchFoundCard';
import '../../styles/HomePage.css';

export function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [quickJoining, setQuickJoining] = useState(false);
  const [showQuickMatch, setShowQuickMatch] = useState(false);
  const [matchResult, setMatchResult] = useState(null);

  const matchMutation = useMutation({
    mutationFn: async (tagIds) => {
      const result = await fetchJson('/rooms/match', {
        method: 'POST',
        body: JSON.stringify({ tag_ids: tagIds }),
      });
      if (result.status === 'matched') {
        const detail = await fetchJson(`/rooms/${result.roomId}`);
        return detail;
      }
      throw new Error(result.message || 'No matching room found');
    },
    onSuccess: (room) => {
      setMatchResult(room);
      setQuickJoining(false);
    },
    onError: () => {
      setQuickJoining(false);
      setMatchResult(null);
    },
  });

  const handleQuickJoin = useCallback(() => {
    setShowQuickMatch(true);
    setQuickJoining(true);
    setMatchResult(null);
    const tagIds = user?.tags?.map(t => t.id) || [];
    matchMutation.mutate(tagIds);
  }, [user, matchMutation]);

  const handleCancelMatch = useCallback(() => {
    setShowQuickMatch(false);
    setQuickJoining(false);
    setMatchResult(null);
  }, []);

  const { data: rooms = [], isLoading: roomsLoading } = useQuery({
    queryKey: ['rooms', 'featured'],
    queryFn: () => fetchJson('/rooms?featured=true&limit=6'),
    staleTime: 60_000,
  });

  return (
    <div className="home-page fade-in">
      <QueueOverlay
        visible={showQuickMatch && quickJoining}
        tags={user?.tags?.map(t => t.name) || []}
        onCancel={handleCancelMatch}
      />

      {matchResult && (
        <MatchFoundCard
          room={matchResult}
          participants={[]}
          onJoin={() => {
            const roomId = matchResult.id;
            setMatchResult(null);
            setShowQuickMatch(false);
            navigate(`/rooms/${roomId}`);
          }}
          onDecline={() => setMatchResult(null)}
        />
      )}

      <HeroSection user={user} onQuickJoin={handleQuickJoin} quickJoining={quickJoining} />
      <ProblemSection />
      <PremiumFlowSection />
      <AgentSection />
      <AudienceSection />
      <RoomsSection rooms={rooms} roomsLoading={roomsLoading} navigate={navigate} />
      <StatsSection />
      <FinalShowcaseSection user={user} navigate={navigate} />
    </div>
  );
}
