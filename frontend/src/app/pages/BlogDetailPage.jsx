import { Link, Navigate, useParams } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import { HiArrowLeft, HiBookOpen } from 'react-icons/hi2';
import { getBlogPost } from './blogContent';
import '../../styles/MarketingPages.css';

export function BlogDetailPage() {
  const { slug } = useParams();
  const post = getBlogPost(slug);

  if (!post) return <Navigate to="/blog" replace />;

  return (
    <main className="marketing-page blog-detail fade-in">
      <Container className="blog-detail__container">
        <Link to="/blog" className="blog-detail__back"><HiArrowLeft size={15} /> Back to Blog</Link>
        <article>
          <header className="blog-detail__header">
            <span className="marketing-eyebrow">{post.category}</span>
            <h1>{post.title}</h1>
            <p>{post.excerpt}</p>
            <div className="blog-meta">{post.author} · {post.date} · {post.readTime}</div>
          </header>
          <div className="blog-detail__hero"><HiBookOpen size={46} /><span>{post.hero}</span></div>
          <div className="blog-detail__content">
            {post.content.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          </div>
          <footer className="blog-detail__footer">
            <h2>Practice this idea in a live room</h2>
            <p>Open a meeting, choose one sentence goal, and let E-Room keep the feedback loop visible.</p>
            <Button as={Link} to="/learning" variant="primary" className="rounded-pill px-4 fw-semibold">Find a meeting</Button>
          </footer>
        </article>
      </Container>
    </main>
  );
}
