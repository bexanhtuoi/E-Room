const React = require('react');

function LiveKitRoom({ children }) { return React.createElement('div', null, children); }
function VideoConference() { return React.createElement('div', null, 'Video Conference'); }
function AudioConference() { return React.createElement('div', null); }
function ControlBar() { return React.createElement('div', null); }
function RoomAudioRenderer() { return React.createElement('div', null); }
function useTracks() { return []; }
function useLocalParticipant() { return { name: 'test' }; }

module.exports = {
  LiveKitRoom,
  VideoConference,
  AudioConference,
  ControlBar,
  RoomAudioRenderer,
  useTracks,
  useLocalParticipant,
};
