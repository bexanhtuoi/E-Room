import { Link } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import { HiArrowRight, HiNewspaper } from 'react-icons/hi2';
import { blogPosts } from './blogContent';
import '../../styles/MarketingPages.css';

export function BlogPage() {
  const [lead, ...rest] = blogPosts;

  return (
    <main className="marketing-page blog-index fade-in">
      <Container className="marketing-page__container">
        <section className="blog-index__header">
          <span className="marketing-eyebrow">E-Room Journal</span>
          <h1>Practical writing for people learning English by speaking.</h1>
          <p>Room routines, feedback habits, and host guides written for learners who want visible progress after every conversation.</p>
        </section>

        <section className="blog-layout" aria-label="Latest blog posts">
          <article className="blog-lead">
            <Link to={`/blog/${lead.slug}`} className="blog-lead__media">
              <HiNewspaper size={44} />
              <span>{lead.hero}</span>
            </Link>
            <div className="blog-lead__body">
              <span>{lead.category}</span>
              <h2><Link to={`/blog/${lead.slug}`}>{lead.title}</Link></h2>
              <p>{lead.excerpt}</p>
              <div className="blog-meta">{lead.author} · {lead.date} · {lead.readTime}</div>
            </div>
          </article>

          <div className="blog-side-list">
            {rest.map((post) => (
              <article className="blog-row" key={post.slug}>
                <div className="blog-row__thumb"><span>{post.hero}</span></div>
                <div>
                  <span>{post.category}</span>
                  <h2><Link to={`/blog/${post.slug}`}>{post.title}</Link></h2>
                  <p>{post.excerpt}</p>
                  <Link to={`/blog/${post.slug}`} className="blog-read-link">Read article <HiArrowRight size={14} /></Link>
                </div>
              </article>
            ))}
          </div>
        </section>
      </Container>
    </main>
  );
}
