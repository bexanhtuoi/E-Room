// Thu tu hien thi: live (active) → open (idle) → ended,
// trong moi trang thai moi nhat (id lon nhat) len truoc.
export const ROOM_STATUS_ORDER = {
  active: 0,
  idle: 1,
  ended: 2,
};

export function roomStatusRank(status) {
  return ROOM_STATUS_ORDER[status] ?? 3;
}

export function sortRooms(rooms) {
  return [...(rooms || [])].sort((a, b) => {
    const rank = roomStatusRank(a.status) - roomStatusRank(b.status);
    if (rank !== 0) return rank;
    return (b.id || 0) - (a.id || 0);
  });
}
