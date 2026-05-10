import { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Badge from 'react-bootstrap/Badge';
import Spinner from 'react-bootstrap/Spinner';
import Form from 'react-bootstrap/Form';
import Modal from 'react-bootstrap/Modal';
import ProgressBar from 'react-bootstrap/ProgressBar';
import {
  HiAcademicCap, HiPlayCircle, HiPlusCircle, HiFunnel, HiUsers,
  HiGlobeAlt, HiClock, HiLanguage, HiUser, HiSparkles,
  HiBolt, HiMagnifyingGlass, HiCheckCircle, HiExclamationTriangle,
  HiArrowRight, HiXMark, HiRocketLaunch, HiStar
} from 'react-icons/hi2';
import { FiSearch, FiRefreshCw, FiZap } from 'react-icons/fi';
import { fetchJson } from '../../lib/api';
import { useAuth } from '../../app/AuthContext';
import { CreateRoomModal } from '../../features/rooms/CreateRoomModal';

const STATUS_ICON = {
  ACTIVE: { icon: HiPlayCircle, color: 'var(--color-success)', badge: 'success', label: 'Live' },
  IDLE: { icon: HiClock, color: 'var(--color-text-muted)', badge: 'info', label: 'Waiting' },
};

function RoomCard({ room }) {
  const status = STATUS_ICON[room.status] || STATUS_ICON.IDLE;
  const StatusIcon = status.icon;
  const level = room.english_level || 'any';
  const tags = room.tags || [];
  const current = room.current_participants || 0;
  const max = room.max_participants || 5;

  return (
    <Card className="h-100 border-0 room-card-v2 fade-in" style={{
      borderRadius: 16, overflow: 'hidden',
      background: 'var(--color-bg-elevated)',
      boxShadow: 'var(--shadow-card)',
      transition: 'all 0.25s ease',
    }}>
      <Card.Body className="d-flex flex-column justify-content-between gap-1 p-4">

        <div className="d-flex justify-content-between align-items-start gap-2">
          <Card.Title style={{
            fontFamily: "'Nunito', sans-serif", fontWeight: 800,
            fontSize: '1.05rem', margin: 0, color: 'var(--color-text-primary)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            flex: 1, minWidth: 0,
          }}>
            {room.topic || room.name || 'Untitled'}
          </Card.Title>
          <Badge bg={status.badge} pill className="text-uppercase fw-semibold flex-shrink-0"
            style={{ fontSize: '0.62rem', padding: '4px 10px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <StatusIcon size={12} /> {status.label}
            </span>
          </Badge>
        </div>

        <Card.Text style={{
          color: 'var(--color-text-secondary)', fontSize: '0.83rem',
          lineHeight: 1.55,
          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
        }}>
          {room.description || 'Join this room to practice English speaking skills.'}
        </Card.Text>

        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '3px 10px', borderRadius: 99, marginBottom: 12,
          background: 'var(--color-accent-muted)', color: 'var(--color-accent)',
          fontSize: '0.68rem', fontWeight: 700, alignSelf: 'flex-start',
        }}>
          <HiLanguage size={11} /> {level.toUpperCase()}
        </span>

        <div className="d-flex flex-wrap align-items-center gap-2">
          {tags.slice(0, 3).map(tag => (
            <span key={tag} style={{
              display: 'inline-block', padding: '3px 8px',
              background: 'var(--color-bg-surface)',
              color: 'var(--color-text-secondary)',
              borderRadius: 99, fontSize: '0.65rem', fontWeight: 600,
            }}>
              #{tag}
            </span>
          ))}
          {tags.length > 3 && (
            <span style={{
              fontSize: '0.6rem', color: 'var(--color-text-muted)', fontWeight: 600,
            }}>
              +{tags.length - 3}
            </span>
          )}
        </div>

        <div className="d-flex justify-content-between align-items-center pt-2" style={{ borderTop: '1px solid var(--color-border)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, color: 'var(--color-text-muted)', fontSize: '0.75rem', fontWeight: 600 }}>
            <HiUsers size={14} /> {current}/{max}
          </span>
          <Link to={`/rooms/${room.id}`} style={{ textDecoration: 'none' }}>
            <button style={{
              padding: '6px 16px', borderRadius: 10,
              background: 'var(--color-accent-gradient)', color: '#fff',
              border: 'none', cursor: 'pointer', fontWeight: 700, fontSize: '0.78rem',
              fontFamily: 'inherit', transition: 'all 0.2s',
              display: 'flex', alignItems: 'center', gap: 5,
            }}
            onMouseOver={e => { e.currentTarget.style.transform = 'scale(1.05)'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(99,102,241,0.3)'; }}
            onMouseOut={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.boxShadow = 'none'; }}
            >
              Join <HiArrowRight size={13} />
            </button>
          </Link>
        </div>
      </Card.Body>
    </Card>
  );
}

function MatchResultCard({ room, onJoin, onRetry, onClose }) {
  const status = STATUS_ICON[room.status] || STATUS_ICON.IDLE;
  const StatusIcon = status.icon;

  return (
    <div className="scale-in p-4 rounded-4"
      style={{
        background: 'var(--color-bg-elevated)',
        border: '2px solid var(--color-success)',
        boxShadow: 'var(--shadow-glow)',
        maxWidth: 420, width: '100%',
      }}>
      <div className="text-center mb-3">
        <div className="d-inline-flex align-items-center justify-content-center rounded-circle mb-2"
          style={{ width: 56, height: 56, background: 'var(--color-success-muted)' }}>
          <HiCheckCircle size={32} style={{ color: 'var(--color-success)' }} />
        </div>
        <h5 className="fw-extrabold mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>Match Found!</h5>
        <p className="text-muted small mb-0">We found a great room for you</p>
      </div>

      <div className="p-3 rounded-3 mb-3" style={{ background: 'var(--color-bg-surface)' }}>
        <div className="d-flex align-items-center gap-2 mb-2">
          <StatusIcon size={18} style={{ color: status.color }} />
          <h6 className="fw-bold mb-0">{room.topic || room.name || 'Untitled'}</h6>
          <Badge bg={status.badge} pill style={{ fontSize: '0.6rem' }}>{status.label}</Badge>
        </div>
        <p className="text-muted small mb-2">{room.description || 'Join this room to practice English.'}</p>
        <div className="d-flex flex-wrap gap-1 mb-2">
          {room.tags?.slice(0, 4).map(tag => (
            <span key={tag} className="rounded-pill fw-medium"
              style={{ display: 'inline-block', padding: '0.25em 0.65em', background: 'var(--color-accent-muted)', color: 'var(--color-accent)', fontSize: '0.62rem', fontWeight: 600 }}>
              #{tag}
            </span>
          ))}
        </div>
        <div className="d-flex gap-3 text-muted small">
          <span className="d-flex align-items-center gap-1"><HiUsers size={14} /> {room.current_participants || 0}/{room.max_participants || 5}</span>
          <span className="d-flex align-items-center gap-1"><HiLanguage size={14} /> {room.english_level || 'any'}</span>
        </div>
      </div>

      <div className="d-flex gap-2">
        <Link to={`/rooms/${room.id}`} className="flex-grow-1" onClick={onJoin}>
          <Button variant="primary" className="w-100 fw-semibold rounded-pill d-flex align-items-center justify-content-center gap-2">
            Join Room <HiArrowRight size={16} />
          </Button>
        </Link>
        <Button variant="outline-secondary" className="rounded-pill px-3" onClick={onRetry} title="Try another match">
          <FiRefreshCw size={16} />
        </Button>
        <Button variant="outline-secondary" className="rounded-pill px-3" onClick={onClose} title="Close">
          <HiXMark size={16} />
        </Button>
      </div>
    </div>
  );
}

const MATCH_STEPS = [
  'Analyzing your profile...',
  'Finding available rooms...',
  'Checking skill compatibility...',
  'Selecting best match...',
];

const MATCH_INTERESTS = ['casual', 'business', 'technology', 'travel', 'education', 'ielts', 'daily', 'pronunciation'];
const MATCH_LEVELS = ['beginner', 'intermediate', 'advanced'];

export function LearningPage() {
  const { user } = useAuth();
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

  const [matchOpen, setMatchOpen] = useState(false);
  const [matchStep, setMatchStep] = useState(0);
  const [matchResult, setMatchResult] = useState(null);
  const [matchError, setMatchError] = useState(null);
  const [matchConfig, setMatchConfig] = useState({
    level: '',
    interests: [],
  });
  const [showConfig, setShowConfig] = useState(false);
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [visibleCount, setVisibleCount] = useState(30);
  const loadMoreRef = useRef(null);

  async function loadRooms() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchJson('/rooms');
      setRooms(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
      setRooms([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadRooms(); }, []);

  function scoreRoom(room, config) {
    let score = 0;

    if (room.status === 'ACTIVE') score += 30;
    else if (room.status === 'IDLE') score += 10;

    const current = room.current_participants || 0;
    const max = room.max_participants || 5;
    if (current < max) score += 20 - Math.floor((current / max) * 10);

    if (config.level && room.english_level) {
      if (room.english_level.toLowerCase() === config.level.toLowerCase()) score += 25;
    }

    if (config.interests?.length > 0 && room.tags) {
      const roomTags = room.tags.map(t => t.toLowerCase());
      config.interests.forEach(interest => {
        roomTags.forEach(rt => {
          if (rt.includes(interest.toLowerCase()) || interest.toLowerCase().includes(rt)) {
            score += 15;
          }
        });
      });
    }

    if (current > 0) score += 5;

    if (room.description && room.description.length > 30) score += 5;

    return score;
  }

  const startQuickMatch = useCallback(() => {
    if ((rooms || []).length === 0) {
      setMatchError('No rooms available. Please try again later.');
      setMatchOpen(true);
      return;
    }

    setMatchOpen(true);
    setMatchResult(null);
    setMatchError(null);
    setMatchStep(0);

    const config = { ...matchConfig };
    const steps = [...MATCH_STEPS];
    let currentStep = 0;

    const interval = setInterval(() => {
      currentStep++;
      if (currentStep < steps.length) {
        setMatchStep(currentStep);
      } else {
        clearInterval(interval);

        try {
          const scored = rooms
            .filter(r => {
              const current = r.current_participants || 0;
              const max = r.max_participants || 5;
              return current < max;
            })
            .map(room => ({ room, score: scoreRoom(room, config) }))
            .filter(({ score }) => score > 0)
            .sort((a, b) => b.score - a.score);

          if (scored.length === 0) {
            setMatchError('No suitable rooms found. Try adjusting your preferences or browse manually.');
          } else {

            const top = scored.slice(0, Math.min(3, scored.length));
            const pick = top[Math.floor(Math.random() * top.length)];
            setMatchResult(pick.room);
          }
        } catch (err) {
          setMatchError('Something went wrong during matching. Please try again.');
        }
      }
    }, 700);

    return () => clearInterval(interval);
  }, [rooms, matchConfig]);

  function resetMatch() {
    setMatchOpen(false);
    setMatchResult(null);
    setMatchError(null);
    setMatchStep(0);
  }

  const filtered = (rooms || []).filter(r => {
    if (filter !== 'all') {
      const rStatus = (r.status || '').toUpperCase();
      if (filter === 'ACTIVE' && rStatus !== 'ACTIVE') return false;
      if (filter === 'IDLE' && rStatus === 'ACTIVE') return false;
    }
    if (search && !r.topic?.toLowerCase().includes(search.toLowerCase())
      && !r.description?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const hasMore = visibleCount < filtered.length;
  const visibleRooms = filtered.slice(0, visibleCount);

  useEffect(() => {
    const el = loadMoreRef.current;
    if (!el || !hasMore) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisibleCount(prev => prev + 30); },
      { rootMargin: '200px' }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore]);

  const filters = [
    { key: 'all', label: 'All', icon: HiGlobeAlt },
    { key: 'ACTIVE', label: 'Live', icon: HiPlayCircle },
    { key: 'IDLE', label: 'Waiting', icon: HiClock },
  ];

  const stats = [
    { label: 'Total Rooms', value: (rooms || []).length, icon: HiGlobeAlt, color: 'var(--color-accent)' },
    { label: 'Live Now', value: (rooms || []).filter(r => r.status === 'ACTIVE').length, icon: HiPlayCircle, color: 'var(--color-success)' },
    { label: 'Waiting', value: (rooms || []).filter(r => r.status === 'IDLE').length, icon: HiClock, color: 'var(--color-text-muted)' },
    { label: 'Your Sessions', value: '0', icon: HiAcademicCap, color: 'var(--color-text-muted)' },
  ];

  return (
    <div className="learning-page fade-in" style={{ minHeight: '80vh' }}>
      <Container className="py-4">

        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
          <div>
            <h2 className="fw-extrabold mb-1 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
              <HiAcademicCap size={28} style={{ color: 'var(--color-accent)' }} />
              Learning Rooms
            </h2>
            <p className="text-muted mb-0">Find a room, join a conversation, improve your English</p>
          </div>
          <div className="d-flex gap-2 flex-wrap">

            <Button
              variant="primary"
              size="sm"
              className="rounded-pill d-flex align-items-center gap-1 fw-semibold px-3 pulse-glow"
              onClick={() => {
                if (matchConfig.level || matchConfig.interests?.length > 0) {
                  startQuickMatch();
                } else {
                  setShowConfig(true);
                }
              }}
              disabled={loading}
            >
              <HiBolt size={16} /> Quick Match
            </Button>
            <Button variant="outline-secondary" size="sm" className="rounded-pill d-flex align-items-center gap-1"
              onClick={loadRooms} disabled={loading}>
              <FiRefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
            </Button>
            <Button variant="primary" size="sm" className="rounded-pill d-flex align-items-center gap-1 fw-semibold px-3"
              style={{ background: 'var(--color-accent-gradient)' }}
              onClick={() => setShowCreateRoom(true)}>
              <HiPlusCircle size={16} /> Create Room
            </Button>
          </div>
        </div>

        <Row className="mb-4 g-2">
          {stats.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <Col xs={6} md={3} key={i}>
                <Card className="border-0 shadow-sm h-100 stat-card">
                  <Card.Body className="p-3 d-flex align-items-center gap-3">
                    <div className="d-flex align-items-center justify-content-center rounded-3"
                      style={{ width: 40, height: 40, background: `${stat.color}18` }}>
                      <Icon size={20} style={{ color: stat.color }} />
                    </div>
                    <div>
                      <div className="fw-bold fs-5 lh-1" style={{ color: 'var(--color-text-primary)' }}>{stat.value}</div>
                      <small className="text-muted">{stat.label}</small>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            );
          })}
        </Row>

        <div className="d-flex flex-column flex-md-row gap-3 mb-4">
          <div className="d-flex gap-1 flex-wrap">
            {filters.map(f => {
              const Icon = f.icon;
              const active = filter === f.key;
              return (
                <Button key={f.key} variant={active ? 'primary' : 'outline-secondary'} size="sm"
                  className={`rounded-pill px-3 d-flex align-items-center gap-1 ${active ? 'fw-semibold' : ''}`}
                  onClick={() => setFilter(f.key)}
                >
                  <Icon size={14} /> {f.label}
                </Button>
              );
            })}
          </div>
          <div className="flex-grow-1" style={{ maxWidth: 320 }}>
            <div className="position-relative">
              <FiSearch size={16} className="position-absolute top-50 translate-middle-y ms-3"
                style={{ color: 'var(--color-text-muted)', zIndex: 5 }} />
              <Form.Control type="text" placeholder="Search rooms..."
                value={search} onChange={e => setSearch(e.target.value)}
                className="rounded-pill ps-5" style={{ fontSize: '0.85rem' }} />
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-5">
            <Spinner animation="border" variant="primary" />
            <p className="text-muted mt-2">Loading rooms...</p>
          </div>
        ) : error ? (
          <div className="text-center py-5">
            <HiExclamationTriangle size={64} className="mb-3" style={{ color: 'var(--color-warning)' }} />
            <h5 className="fw-bold">Couldn't load rooms</h5>
            <p className="text-muted mb-3">{error}</p>
            <Button variant="primary" className="rounded-pill px-4" onClick={loadRooms}>Try Again</Button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-5">
            <HiAcademicCap size={64} className="mb-3" style={{ color: 'var(--color-text-muted)' }} />
            <h5 className="fw-bold">{search || filter !== 'all' ? 'No matching rooms' : 'No rooms yet'}</h5>
            <p className="text-muted mb-3">
              {search || filter !== 'all'
                ? 'Try a different search or filter.'
                : 'Be the first to create a learning room!'}
            </p>
            {!search && filter === 'all' && (
              <Button variant="primary" className="rounded-pill px-4 d-flex align-items-center gap-1 mx-auto">
                <HiPlusCircle size={18} /> Create First Room
              </Button>
            )}
          </div>
        ) : (
          <>
            <Row>
              {visibleRooms.map((room, idx) => (
                <Col key={room.id || idx} md={6} lg={4} className="mb-3 stagger-1"
                  style={{ animationDelay: `${(idx % 30) * 0.05}s` }}>
                  <RoomCard room={room} />
                </Col>
              ))}
            </Row>
            {hasMore && (
              <div className="text-center py-3">
                <Spinner animation="border" size="sm" variant="primary" />
                <span className="ms-2 text-muted">Loading more rooms...</span>
              </div>
            )}
            <div ref={loadMoreRef} style={{ height: 1 }} />
          </>
        )}
      </Container>

      <Modal show={showConfig} onHide={() => setShowConfig(false)} centered contentClassName="bg-transparent border-0">
        <div className="p-4 rounded-4 scale-in"
          style={{
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)',
            boxShadow: 'var(--shadow-lg)',
          }}>
          <div className="text-center mb-4">
            <div className="d-inline-flex align-items-center justify-content-center rounded-circle mb-2"
              style={{ width: 56, height: 56, background: 'var(--color-accent-muted)' }}>
              <HiBolt size={28} style={{ color: 'var(--color-accent)' }} />
            </div>
            <h5 className="fw-extrabold mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>Quick Match</h5>
            <p className="text-muted small mb-0">Tell us your preferences and we'll find the perfect room</p>
          </div>

          <Form.Group className="mb-3">
            <Form.Label className="fw-semibold small" style={{ color: 'var(--color-text-secondary)' }}>
              Your English Level
            </Form.Label>
            <div className="d-flex gap-2 flex-wrap">
              {MATCH_LEVELS.map(lvl => (
                <Button key={lvl}
                  variant={matchConfig.level === lvl ? 'primary' : 'outline-secondary'}
                  size="sm" className="rounded-pill text-capitalize"
                  onClick={() => setMatchConfig(prev => ({ ...prev, level: prev.level === lvl ? '' : lvl }))}
                >
                  {lvl}
                </Button>
              ))}
            </div>
          </Form.Group>

          <Form.Group className="mb-4">
            <Form.Label className="fw-semibold small" style={{ color: 'var(--color-text-secondary)' }}>
              Topics You're Interested In
            </Form.Label>
            <div className="d-flex gap-2 flex-wrap">
              {MATCH_INTERESTS.map(interest => (
                <Button key={interest}
                  variant={matchConfig.interests.includes(interest) ? 'primary' : 'outline-secondary'}
                  size="sm" className="rounded-pill text-capitalize"
                  onClick={() => setMatchConfig(prev => ({
                    ...prev,
                    interests: prev.interests.includes(interest)
                      ? prev.interests.filter(i => i !== interest)
                      : [...prev.interests, interest],
                  }))}
                >
                  {interest}
                </Button>
              ))}
            </div>
          </Form.Group>

          <div className="d-flex gap-2">
            <Button variant="primary" className="flex-grow-1 rounded-pill fw-semibold d-flex align-items-center justify-content-center gap-2"
              onClick={() => { setShowConfig(false); startQuickMatch(); }}>
              <HiBolt size={16} /> Find My Room
            </Button>
            <Button variant="outline-secondary" className="rounded-pill px-3" onClick={() => setShowConfig(false)}>
              <HiXMark size={16} />
            </Button>
          </div>

          <div className="text-center mt-3">
            <Button variant="link" size="sm" className="text-decoration-none"
              style={{ color: 'var(--color-text-muted)', fontSize: '0.75rem' }}
              onClick={() => { setShowConfig(false); startQuickMatch(); }}>
              Skip & try with defaults
            </Button>
          </div>
        </div>
      </Modal>

      <Modal show={matchOpen && !matchResult && !matchError} onHide={resetMatch} centered
        contentClassName="bg-transparent border-0">
        <div className="p-5 rounded-4 text-center"
          style={{
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-border)',
            boxShadow: 'var(--shadow-lg)',
            minWidth: 320,
          }}>
          <div className="d-inline-flex align-items-center justify-content-center rounded-circle mb-3 pulse-glow"
            style={{ width: 72, height: 72, background: 'var(--color-accent-muted)' }}>
            <HiMagnifyingGlass size={36} style={{ color: 'var(--color-accent)' }} />
          </div>
          <ProgressBar now={(matchStep + 1) * 25} className="mb-3" style={{ height: 4, borderRadius: 2 }} />
          <p className="fw-semibold mb-0" style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
            {MATCH_STEPS[matchStep]}
          </p>
          <small className="text-muted">Please wait a moment...</small>
        </div>
      </Modal>

      <Modal show={matchOpen && (matchResult || matchError)} onHide={resetMatch} centered
        contentClassName="bg-transparent border-0">
        {matchResult ? (
          <MatchResultCard
            room={matchResult}
            onJoin={resetMatch}
            onRetry={() => { setMatchResult(null); setMatchError(null); setMatchStep(0); startQuickMatch(); }}
            onClose={resetMatch}
          />
        ) : matchError ? (
          <div className="p-4 rounded-4 scale-in" style={{
            background: 'var(--color-bg-elevated)',
            border: '2px solid var(--color-warning)',
            boxShadow: 'var(--shadow-lg)',
            maxWidth: 400, width: '100%',
          }}>
            <div className="text-center mb-3">
              <div className="d-inline-flex align-items-center justify-content-center rounded-circle mb-2"
                style={{ width: 56, height: 56, background: 'var(--color-warning-muted)' }}>
                <HiExclamationTriangle size={32} style={{ color: 'var(--color-warning)' }} />
              </div>
              <h5 className="fw-extrabold mb-1" style={{ fontFamily: 'Nunito, sans-serif' }}>No Match</h5>
              <p className="text-muted small mb-0">{matchError}</p>
            </div>
            <div className="d-flex gap-2">
              <Button variant="outline-secondary" className="flex-grow-1 rounded-pill" onClick={resetMatch}>
                Browse Manually
              </Button>
              <Button variant="primary" className="flex-grow-1 rounded-pill fw-semibold"
                onClick={() => { setMatchResult(null); setMatchError(null); setMatchStep(0); startQuickMatch(); }}>
                Try Again
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>

      {showCreateRoom && (
        <CreateRoomModal
          onClose={() => setShowCreateRoom(false)}
          onRoomCreated={(room) => { setShowCreateRoom(false); loadRooms(); }}
        />
      )}

      <style>{`
        .learning-page .room-card { transition: transform 0.2s ease, box-shadow 0.2s ease; }
        .learning-page .room-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-lg); }
        .learning-page .stat-card { transition: transform 0.15s ease; }
        .learning-page .stat-card:hover { transform: translateY(-1px); }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 0.8s linear infinite; }
      `}</style>
    </div>
  );
}
