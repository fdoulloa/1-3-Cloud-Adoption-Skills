package cmd

import (
	"testing"

	"google.golang.org/api/people/v1"
)

func TestPrimaryName_EdgeCases(t *testing.T) {
	if got := primaryName(nil); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}
	if got := primaryName(&people.Person{}); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}
	if got := primaryName(&people.Person{Names: []*people.Name{nil}}); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}

	p1 := &people.Person{Names: []*people.Name{{DisplayName: "Ada Lovelace"}}}
	if got := primaryName(p1); got != "Ada Lovelace" {
		t.Fatalf("unexpected: %q", got)
	}

	p2 := &people.Person{Names: []*people.Name{{GivenName: "Ada", FamilyName: "Lovelace"}}}
	if got := primaryName(p2); got != "Ada Lovelace" {
		t.Fatalf("unexpected: %q", got)
	}
}

func TestPrimaryEmailAndPhone_EdgeCases(t *testing.T) {
	if got := primaryEmail(nil); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}
	if got := primaryEmail(&people.Person{}); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}
	if got := primaryEmail(&people.Person{EmailAddresses: []*people.EmailAddress{nil}}); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}
	if got := primaryEmail(&people.Person{EmailAddresses: []*people.EmailAddress{{Value: "a@b.com"}}}); got != "a@b.com" {
		t.Fatalf("unexpected: %q", got)
	}

	if got := primaryPhone(nil); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}
	if got := primaryPhone(&people.Person{}); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}
	if got := primaryPhone(&people.Person{PhoneNumbers: []*people.PhoneNumber{nil}}); got != "" {
		t.Fatalf("expected empty, got %q", got)
	}
	if got := primaryPhone(&people.Person{PhoneNumbers: []*people.PhoneNumber{{Value: "+1"}}}); got != "+1" {
		t.Fatalf("unexpected: %q", got)
	}
}
