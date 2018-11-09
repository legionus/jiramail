package syncer

import (
	"fmt"
	"path"
	"strings"

	"github.com/andygrunwald/go-jira"
	"github.com/sirupsen/logrus"

	"github.com/legionus/jiramail/internal/jiraconv"
	"github.com/legionus/jiramail/internal/jiraplus"
)

func (s *JiraSyncer) sprint(parent string, board *jira.Board, sprint *jira.Sprint, refs []string) error {
	logmsg := fmt.Sprintf("remote %q, board %q, sprint %q", s.remote, board.Name, sprint.Name)
	logrus.Infof("%s begin to process", logmsg)

	mdir, err := Maildir(path.Join(parent, "sprints", fmt.Sprintf("%s (%d)", ReplaceStringTrash(sprint.Name), sprint.ID)))
	if err != nil {
		return err
	}

	// write sprint to the sprint maildir
	msg, err := s.converter.Sprint(sprint, append(refs, jiraconv.BoardMessageID(board)))
	if err != nil {
		return err
	}

	err = s.writeMessage(mdir, msg)
	if err != nil {
		return err
	}

	// write board to the sprint maildir
	msg, err = s.converter.Board(board, "nobody@jira", refs)
	if err != nil {
		return err
	}

	err = s.writeMessage(mdir, msg)
	if err != nil {
		return err
	}

	if strings.ToLower(sprint.State) != "active" {
		logrus.Infof("%s, issues are not handled because sprint is not active", logmsg)
		return nil
	}

	refs = append(refs, jiraconv.BoardMessageID(board), jiraconv.SprintMessageID(sprint))

	opts := &jiraplus.BoardIssuesSearchOptions{}
	opts.MaxResults = 100
	opts.Fields = []string{"*all"}

	count, err := jiraplus.List(
		func(i int) ([]interface{}, error) {
			opts.StartAt = i

			ret, _, err := s.client.PlusBoard.GetIssuesForSprint(sprint.OriginBoardID, sprint.ID, opts)
			if err != nil {
				return nil, fmt.Errorf("unable to get issues for sprint '%s': %s", sprint.Name, err)
			}

			if ret.Total <= i {
				return nil, nil
			}

			a := make([]interface{}, len(ret.Issues))

			for k := range ret.Issues {
				a[k] = ret.Issues[k]
			}

			return a, nil
		},
		func(o interface{}) error {
			issue := o.(*jira.Issue)

			if issue.Fields == nil || issue.Fields.Type.Subtask {
				return nil
			}

			if err := s.issue(mdir, issue, refs); err != nil {
				return err
			}

			if err := s.projectissue(issue); err != nil {
				return err
			}

			return nil
		},
	)
	if err != nil {
		return err
	}

	logrus.Infof("%s, %d issues handled", logmsg, count)

	// Garbage collection
	err = s.CleanDir(mdir)
	if err != nil {
		return err
	}

	return nil
}

func (s *JiraSyncer) sprints(parent string, board *jira.Board, refs []string) error {
	opts := &jira.GetAllSprintsOptions{}
	opts.MaxResults = 100

	_, err := jiraplus.List(
		func(i int) ([]interface{}, error) {
			opts.StartAt = i

			ret, _, err := s.client.Board.GetAllSprintsWithOptions(board.ID, opts)
			if err != nil {
				return nil, err
			}

			a := make([]interface{}, len(ret.Values))

			for k := range ret.Values {
				a[k] = &ret.Values[k]
			}

			return a, nil
		},
		func(o interface{}) error {
			sprint := o.(*jira.Sprint)

			err := s.sprint(parent, board, sprint, refs)
			if err != nil {
				return err
			}

			return nil
		},
	)

	return err
}
