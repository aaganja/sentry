import React from 'react';
import styled from '@emotion/styled';

import Link from 'app/components/links/link';
import Tooltip from 'app/components/tooltip';
import {t} from 'app/locale';
import space from 'app/styles/space';
import overflowEllipsis from 'app/styles/overflowEllipsis';
import {Event, OrganizationSummary} from 'app/types';
import Version from 'app/components/versionV2';

import EventView from './eventView';
import {getExpandedResults} from './utils';
import {SectionHeading} from './styles';

type Props = {
  organization: OrganizationSummary;
  event: Event;
  eventView: EventView;
};

const TagsTable = (props: Props) => {
  const {organization, event, eventView} = props;
  const tags = event.tags;
  return (
    <StyledTagsTable>
      <SectionHeading>{t('Event Tag Details')}</SectionHeading>
      <StyledTable>
        <tbody>
          {tags.map(tag => {
            let target, tagValue;
            const tagInQuery = eventView.query.includes(`${tag.key}:`);
            if (!tagInQuery) {
              const nextView = getExpandedResults(
                eventView,
                {[tag.key]: tag.value},
                event
              );
              target = nextView.getResultsViewUrlTarget(organization.slug);
            }

            switch (tag.key) {
              case 'release':
                tagValue = <Version version={tag.value} anchor={false} withPackage />;
                break;
              default:
                tagValue = tag.value;
            }

            return (
              <StyledTr key={tag.key}>
                <TagKey>{tag.key}</TagKey>
                <TagValue>
                  {tagInQuery ? (
                    <Tooltip title={t('This tag is in the current filter conditions')}>
                      <span>{tagValue}</span>
                    </Tooltip>
                  ) : (
                    <Link to={target}>{tagValue}</Link>
                  )}
                </TagValue>
              </StyledTr>
            );
          })}
        </tbody>
      </StyledTable>
    </StyledTagsTable>
  );
};

const StyledTagsTable = styled('div')`
  margin-bottom: ${space(3)};
`;

const StyledTable = styled('table')`
  table-layout: fixed;
  width: 100%;
  max-width: 100%;
`;

const StyledTr = styled('tr')`
  &:nth-child(2n + 1) td {
    background: #f4f2f7;
  }
`;

const TagKey = styled('td')`
  color: ${p => p.theme.gray3};
  padding: ${space(0.5)} ${space(1)};
  font-size: ${p => p.theme.fontSizeMedium};
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
`;

const TagValue = styled(TagKey)`
  text-align: right;
  ${overflowEllipsis};
`;

export default TagsTable;
