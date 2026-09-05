import { Link, Navigate, useParams } from 'react-router-dom';
import { Section, Eyebrow, Card } from '../../components/common/UI';
import { BLOG_POSTS } from '../../data/site';

export function BlogDetailPage() {
  const { slug } = useParams();
  const post = BLOG_POSTS.find((p) => p.slug === slug);
  if (!post) return <Navigate to="/blog" replace />;
  const related = BLOG_POSTS.filter((p) => p.slug !== slug).slice(0, 3);

  return (
    <div>
      <Section>
        <div style={{ maxWidth: 780 }}>
          <Link to="/blog" style={{ fontWeight: 800, color: '#111' }}>← Back to blog</Link>
          <div style={{ marginTop: 18 }}><Eyebrow>{post.category}</Eyebrow></div>
          <h1 className="er-h2" style={{ marginTop: 12 }}>{post.title}</h1>
          <p className="er-sub">{post.excerpt}</p>
          <p style={{ fontSize: 13, color: '#666', marginTop: 12 }}>{post.author} • {post.date} • {post.readTime}</p>
          <div style={{ marginTop: 28, display: 'grid', gap: 16 }}>
            {post.body.map((p, i) => (
              <p key={i} style={{ fontSize: 17, lineHeight: 1.75, color: '#222', margin: 0 }}>{p}</p>
            ))}
          </div>
          <Card ink style={{ marginTop: 32 }}>
            <h3>Practice this in a live room</h3>
            <p>Pick one sentence from this article and use it in your next room.</p>
            <div style={{ marginTop: 14 }}><Link className="er-btn" style={{ background: '#fff', color: '#111', borderColor: '#fff', textDecoration: 'none' }} to="/login">Find a room →</Link></div>
          </Card>
          <h3 style={{ marginTop: 40 }}>Related articles</h3>
          <div className="er-grid er-grid--3" style={{ marginTop: 16 }}>
            {related.map((r) => (
              <Card key={r.slug}>
                <span className="er-tag">{r.category}</span>
                <h3><Link to={`/blog/${r.slug}`} style={{ color: '#111' }}>{r.title}</Link></h3>
                <p>{r.excerpt}</p>
              </Card>
            ))}
          </div>
        </div>
      </Section>
    </div>
  );
}
