const React = require('react');

function BrowserRouter({ children }) { return React.createElement(React.Fragment, null, children); }
function Navigate() { return null; }
function Route() { return null; }
function Routes({ children }) { return React.createElement(React.Fragment, null, children); }
function useNavigate() { return () => {}; }
function useParams() { return {}; }
function useLocation() { return { pathname: '/' }; }
function Link({ children }) { return React.createElement('a', { href: '#' }, children); }

module.exports = {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
  useLocation,
  Link,
};
