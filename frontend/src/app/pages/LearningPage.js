import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Row from 'react-bootstrap/Row';
import Col from 'react-bootstrap/Col';
import Card from 'react-bootstrap/Card';
import Button from 'react-bootstrap/Button';
import Badge from 'react-bootstrap/Badge';
import Spinner from 'react-bootstrap/Spinner';
import Form from 'react-bootstrap/Form';
import { HiAcademicCap, HiPlayCircle, HiPlusCircle, HiFunnel, HiUsers, HiGlobeAlt, HiClock, HiLanguage } from 'react-icons/hi2';
import { FiSearch, FiRefreshCw } from 'react-icons/fi';
import { fetchJson } from '../../lib/api';

const STATUS_ICON = {
  ACTIVE: { icon: HiPlayCircle, color: 'var(--color-success)', badge: 'success', label: 'Live' },
  MATCHING: { icon: HiUsers, color: 'var(--color-warning)', badge: 'warning', label: 'Matching' },
  IDLE: { icon: HiClock, color: 'var(--color-text-muted)', badge: 'info', label: 'Waiting' },
  END: { icon: HiClock, color: 'var(--color-text-muted)', badge: 'secondary', label: 'Ended' },
};

function RoomCard({ room }) {
  const status = STATUS_ICON[room.status] || STATUS_ICON.IDLE;
  const StatusIcon = status.icon;

  return (
    <Card className="h-100 border-0 shadow-sm room-card fade-in">
      <Card.Body className="d-flex flex-column p-3">
        <div className="d-flex justify-content-between align-items-start mb-2">
          <div className="d-flex align-items-center gap-2">
            <StatusIcon size={18} style={{ color: status.color }} />
            <Card.Title className="fw-bold mb-0 fs-6">{room.topic || room.name || 'Untitled'}</Card.Title>
          </div>
          <Badge bg={status.badge} pill className="text-uppercase fw-semibold" style={{ fontSize: '0.6rem' }}>{status.label}</Badge>
        </div>
        <Card.Text className="text-muted small mb-3 flex-grow-1" style={{ lineHeight: 1.5 }}>
          {room.description || 'Join this room to practice English.'}
        </Card.Text>
        <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
          {room.tags && [...room.tags].slice(0, 3).map(tag => (
            <Badge key={tag} bg="light" text="dark" className="rounded-pill fw-medium" style={{ fontSize: '0.65rem', background: 'var(--color-accent-muted) !important', color: 'var(--color-accent) !important' }}>
              #{tag}
            </Badge>
          ))}
        </div>
        <div className="d-flex justify-content-between align-items-center mt-auto pt-2 border-top" style={{ borderColor: 'var(--color-border)' }}>
          <div className="d-flex align-items-center gap-3 text-muted small">
            <span className="d-flex align-items-center gap-1"><HiUsers size={14} /> {room.current_participants || 0}/{room.max_participants || 5}</span>
            <span className="d-flex align-items-center gap-1"><HiLanguage size={14} /> {room.english_level || 'any'}</span>
          </div>
          <Link to={`/rooms/${room.id}`}>
            <Button variant="outline-primary" size="sm" className="rounded-pill px-3 fw-semibold">Join</Button>
          </Link>
        </div>
      </Card.Body>
    </Card>
  );
}

export function LearningPage() {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');
  const [search, setSearch] = useState('');

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

  const filtered = rooms.filter(r => {
    if (filter !== 'all' && r.status !== filter) return false;
    if (search && !r.topic?.toLowerCase().includes(search.toLowerCase()) && !r.description?.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  const filters = [
    { key: 'all', label: 'All', icon: HiGlobeAlt },
    { key: 'ACTIVE', label: 'Live', icon: HiPlayCircle },
    { key: 'MATCHING', label: 'Matching', icon: HiUsers },
    { key: 'IDLE', label: 'Waiting', icon: HiClock },
  ];

  const stats = [
    { label: 'Total Rooms', value: rooms.length, icon: HiGlobeAlt, color: 'var(--color-accent)' },
    { label: 'Live Now', value: rooms.filter(r => r.status === 'ACTIVE').length, icon: HiPlayCircle, color: 'var(--color-success)' },
    { label: 'Matching', value: rooms.filter(r => r.status === 'MATCHING').length, icon: HiUsers, color: 'var(--color-warning)' },
    { label: 'Your Sessions', value: '0', icon: HiAcademicCap, color: 'var(--color-text-muted)' },
  ];

  return (
    <div className="learning-page fade-in" style={{ minHeight: '80vh' }}>
      <Container className="py-4">
        {/* Header */}
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
          <div>
            <h2 className="fw-extrabold mb-1 d-flex align-items-center gap-2" style={{ fontFamily: 'Nunito, sans-serif' }}>
              <HiAcademicCap size={28} style={{ color: 'var(--color-accent)' }} />
              Learning Rooms
            </h2>
            <p className="text-muted mb-0">Find a room, join a conversation, improve your English</p>
          </div>
          <div className="d-flex gap-2">
            <Button variant="outline-secondary" size="sm" className="rounded-pill d-flex align-items-center gap-1" onClick={loadRooms} disabled={loading}>
              <FiRefreshCw size={14} className={loading ? 'spin' : ''} /> Refresh
            </Button>
            <Button variant="primary" size="sm" className="rounded-pill d-flex align-items-center gap-1 fw-semibold px-3">
              <HiPlusCircle size={16} /> Create Room
            </Button>
          </div>
        </div>

        {/* Stats */}
        <Row className="mb-4 g-2">
          {stats.map((stat, i) => {
            const Icon = stat.icon;
            return (
              <Col xs={6} md={3} key={i}>
                <Card className="border-0 shadow-sm h-100 stat-card">
                  <Card.Body className="p-3 d-flex align-items-center gap-3">
                    <div className="d-flex align-items-center justify-content-center rounded-3" style={{ width: 40, height: 40, background: `${stat.color}18` }}>
                      <Icon size={20} style={{ color: stat.color }} />
                    </div>
                    <div>
                      <div className="fw-bold fs-5 lh-1">{stat.value}</div>
                      <small className="text-muted">{stat.label}</small>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            );
          })}
        </Row>

        {/* Filters */}
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
              <FiSearch size={16} className="position-absolute top-50 translate-middle-y ms-3" style={{ color: 'var(--color-text-muted)', zIndex: 5 }} />
              <Form.Control type="text" placeholder="Search rooms..."
                value={search} onChange={e => setSearch(e.target.value)}
                className="rounded-pill ps-5" style={{ fontSize: '0.85rem' }} />
            </div>
          </div>
        </div>

        {/* Room Grid */}
        {loading ? (
          <div className="text-center py-5">
            <Spinner animation="border" variant="primary" />
            <p className="text-muted mt-2">Loading rooms...</p>
          </div>
        ) : error ? (
          <div className="text-center py-5">
            <div className="display-1 mb-3">⚠️</div>
            <h5 className="fw-bold">Couldn't load rooms</h5>
            <p className="text-muted mb-3">{error}</p>
            <Button variant="primary" className="rounded-pill px-4" onClick={loadRooms}>Try Again</Button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-5">
            <HiAcademicCap size={64} className="mb-3" style={{ color: 'var(--color-text-muted)' }} />
            <h5 className="fw-bold">{search || filter !== 'all' ? 'No matching rooms' : 'No rooms yet'}</h5>
            <p className="text-muted mb-3">{search || filter !== 'all' ? 'Try a different search or filter.' : 'Be the first to create a learning room!'}</p>
            {!search && filter === 'all' && (
              <Button variant="primary" className="rounded-pill px-4 d-flex align-items-center gap-1 mx-auto">
                <HiPlusCircle size={18} /> Create First Room
              </Button>
            )}
          </div>
        ) : (
          <Row>
            {filtered.map((room, idx) => (
              <Col key={room.id || idx} md={6} lg={4} className="mb-3 stagger-1" style={{ animationDelay: `${idx * 0.05}s` }}>
                <RoomCard room={room} />
              </Col>
            ))}
          </Row>
        )}
      </Container>

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
