import { Link } from 'react-router-dom';
import Container from 'react-bootstrap/Container';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import { HiArrowRight, HiChatBubbleLeftRight, HiEnvelope, HiMapPin, HiUserGroup } from 'react-icons/hi2';
import '../../styles/MarketingPages.css';

const channels = [
  { icon: HiChatBubbleLeftRight, title: 'Learner support', text: 'Questions about rooms, notes, feedback, or account access.' },
  { icon: HiUserGroup, title: 'Schools and teams', text: 'Run speaking practice for classes, clubs, onboarding, or interview groups.' },
  { icon: HiEnvelope, title: 'Partnerships', text: 'Discuss integrations, content programs, and long-term learning workflows.' },
];

export function ContactPage() {
  return (
    <main className="marketing-page contact-page fade-in">
      <Container className="marketing-page__container contact-page__container">
        <section className="contact-hero">
          <span className="marketing-eyebrow">Contact</span>
          <h1>Get the right support for your speaking program.</h1>
          <p>Tell us whether you are learning alone, hosting rooms, or bringing E-Room to a group. We will route the conversation to the right product path.</p>
          <div className="contact-hero__meta">
            <span><HiMapPin size={16} /> Remote-first support</span>
            <span><HiEnvelope size={16} /> Product and learning help</span>
          </div>
        </section>

        <section className="contact-layout">
          <div className="contact-channels">
            {channels.map((channel) => {
              const Icon = channel.icon;
              return (
                <article key={channel.title}>
                  <Icon size={24} />
                  <div><h2>{channel.title}</h2><p>{channel.text}</p></div>
                </article>
              );
            })}
          </div>

          <Form className="contact-form">
            <div>
              <h2>Send a message</h2>
              <p>Use this form to shape the request before it becomes an email or support ticket.</p>
            </div>
            <Form.Group>
              <Form.Label>Name</Form.Label>
              <Form.Control placeholder="Your name" />
            </Form.Group>
            <Form.Group>
              <Form.Label>Email</Form.Label>
              <Form.Control type="email" placeholder="you@example.com" />
            </Form.Group>
            <Form.Group>
              <Form.Label>What do you need?</Form.Label>
              <Form.Select defaultValue="support">
                <option value="support">Learner support</option>
                <option value="team">School or team plan</option>
                <option value="billing">Billing question</option>
                <option value="partnership">Partnership</option>
              </Form.Select>
            </Form.Group>
            <Form.Group>
              <Form.Label>Message</Form.Label>
              <Form.Control as="textarea" rows={5} placeholder="Tell us about your goal, room format, or issue." />
            </Form.Group>
            <Button type="button" variant="primary" className="rounded-pill fw-semibold px-4">Prepare message <HiArrowRight size={15} /></Button>
          </Form>
        </section>

        <section className="contact-bottom-card">
          <div><span>Prefer action now?</span><h2>Open a meeting room and continue learning while we help.</h2></div>
          <Button as={Link} to="/learning" variant="outline-primary" className="rounded-pill fw-semibold px-4">Go to Meeting</Button>
        </section>
      </Container>
    </main>
  );
}
