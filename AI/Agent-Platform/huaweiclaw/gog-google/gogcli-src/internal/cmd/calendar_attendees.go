package cmd

import (
	"strings"

	"google.golang.org/api/calendar/v3"
)

func buildAttendees(csv string) []*calendar.EventAttendee {
	addrs := splitCSV(csv)
	if len(addrs) == 0 {
		return nil
	}
	out := make([]*calendar.EventAttendee, 0, len(addrs))
	for _, a := range addrs {
		attendee := parseAttendee(a)
		if attendee != nil {
			out = append(out, attendee)
		}
	}
	return out
}

// mergeAttendees preserves existing attendees (with all their metadata like responseStatus)
// and adds new attendees from the CSV string. Duplicates (by email) are skipped.
func mergeAttendees(existing []*calendar.EventAttendee, addCSV string) []*calendar.EventAttendee {
	newEmails := splitCSV(addCSV)
	if len(newEmails) == 0 {
		return existing
	}

	// Build a set of existing emails for deduplication
	existingEmails := make(map[string]bool, len(existing))
	for _, a := range existing {
		if a != nil && a.Email != "" {
			existingEmails[strings.ToLower(a.Email)] = true
		}
	}

	// Start with existing attendees (preserving all metadata)
	out := make([]*calendar.EventAttendee, 0, len(existing)+len(newEmails))
	out = append(out, existing...)

	// Add new attendees that don't already exist
	for _, email := range newEmails {
		if !existingEmails[strings.ToLower(email)] {
			out = append(out, &calendar.EventAttendee{
				Email:          email,
				ResponseStatus: "needsAction",
			})
			existingEmails[strings.ToLower(email)] = true
		}
	}
	return out
}

func parseAttendee(s string) *calendar.EventAttendee {
	s = strings.TrimSpace(s)
	if s == "" {
		return nil
	}
	parts := strings.Split(s, ";")
	email := strings.TrimSpace(parts[0])
	if email == "" {
		return nil
	}

	attendee := &calendar.EventAttendee{Email: email}
	for _, p := range parts[1:] {
		raw := strings.TrimSpace(p)
		lower := strings.ToLower(raw)
		if lower == "optional" {
			attendee.Optional = true
			continue
		}
		if strings.HasPrefix(lower, "comment=") {
			attendee.Comment = strings.TrimSpace(raw[len("comment="):])
		}
	}
	return attendee
}
